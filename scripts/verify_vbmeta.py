#!/usr/bin/env python3
"""Parse AVB vbmeta descriptors and verify each recorded digest against the
actual image files in an extracted package. Read-only; no device access.

This is the diagnostic that localizes "flash succeeded but device won't boot"
to a stale-vbmeta build defect: a hash descriptor whose recorded digest no
longer matches the shipped image (e.g. vendor_boot updated without re-signing).

VBMeta layout reference (avb_vbmeta_image.h): header is 256 bytes; hash and
signature live in the authentication block; descriptors, public key and
key metadata live in the auxiliary block. All *_offset fields are relative to
the START OF THEIR OWN BLOCK, not to the end of the file.

Usage:
  python verify_vbmeta.py --pkg /path/to/extracted_package
"""
import argparse
import hashlib
import os
import struct

ALGS = {b"sha256": hashlib.sha256, b"sha512": hashlib.sha512}


def parse_descriptors(data: bytes) -> list[tuple[int, bytes]]:
    auth_sz, _aux_sz = struct.unpack(">QQ", data[12:28])
    desc_off, desc_sz = struct.unpack(">QQ", data[96:112])
    base = 256 + auth_sz + desc_off
    out, p, end = [], base, base + desc_sz
    while p + 16 <= end:
        tag, num_follow = struct.unpack(">QQ", data[p:p + 16])
        if tag == 0 and num_follow == 0:
            break
        out.append((tag, data[p + 16:p + 16 + num_follow]))
        p += 16 + num_follow  # num_follow includes trailing padding to 8 bytes
    return out


def sha1_of_pubkey(vbmeta_path: str) -> str:
    data = open(vbmeta_path, "rb").read()
    auth_sz, aux_sz = struct.unpack(">QQ", data[12:28])
    pk_off, pk_sz = struct.unpack(">QQ", data[64:80])
    start = 256 + auth_sz + pk_off
    return hashlib.sha1(data[start:start + pk_sz]).hexdigest()


def verify_hash_desc(payload: bytes):
    image_size = struct.unpack(">Q", payload[0:8])[0]
    alg = payload[8:40].split(b"\x00")[0]
    name_len, salt_len, digest_len, _flags = struct.unpack(">IIII", payload[40:56])
    off = 116
    name = payload[off:off + name_len].decode()
    salt = payload[off + name_len:off + name_len + salt_len]
    digest = payload[off + name_len + salt_len:off + name_len + salt_len + digest_len]
    return name, image_size, alg, salt, digest


def hash_image(path: str, image_size: int, alg: bytes, salt: bytes) -> tuple[bytes, int]:
    h = ALGS[alg]()
    h.update(salt)
    remaining = image_size
    with open(path, "rb") as f:
        while remaining > 0:
            chunk = f.read(min(4 * 1024 * 1024, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.digest(), image_size - remaining


def walk_descriptors(pkg: str, vbmeta_name: str, hashes_only: bool = False) -> None:
    vbmeta = os.path.join(pkg, "images", vbmeta_name)
    print("%s pubkey SHA1: %s" % (vbmeta_name, sha1_of_pubkey(vbmeta)))
    descs = parse_descriptors(open(vbmeta, "rb").read())
    print("descriptors in %s: %d" % (vbmeta_name, len(descs)))
    for tag, payload in descs:
        if tag == 0 and not hashes_only:  # property
            kl, vl = struct.unpack(">QQ", payload[0:16])
            print("  [property] %s = %s" % (
                payload[16:16 + kl].decode(), payload[16 + kl:16 + kl + vl].decode()))
        elif tag == 2:  # hash descriptor: the ones that must match shipped images
            name, image_size, alg, salt, digest = verify_hash_desc(payload)
            img = os.path.join(pkg, "images", name + ".img")
            if not os.path.exists(img):
                print("  [hash] %-16s image_size=%-12d  !! no such image file" % (name, image_size))
                continue
            got, _consumed = hash_image(img, image_size, alg, salt)
            ok = got == digest
            print("  [hash] %-16s alg=%-7s size=%-12d %s" % (
                name, alg.decode(), image_size, "MATCH" if ok else "MISMATCH"))
            if not ok:
                print("        expected %s" % digest.hex())
                print("        computed %s" % got.hex())
        elif tag == 1 and not hashes_only:  # hashtree
            image_size, = struct.unpack(">Q", payload[0:8])
            alg = payload[48:80].split(b"\x00")[0]
            name_len = struct.unpack(">I", payload[80:84])[0]
            name = payload[156:156 + name_len].decode()
            print("  [hashtree] %-14s alg=%-7s image_size=%d" % (name, alg.decode(), image_size))
        elif tag == 4 and not hashes_only:  # chain partition
            loc, = struct.unpack(">I", payload[0:4])
            name_len, = struct.unpack(">I", payload[4:8])
            pklen, = struct.unpack(">I", payload[8:12])
            # layout: loc(4) name_len(4) pk_len(4) reserved(64) name(pk at 76)
            name = payload[76:76 + name_len].decode()
            print("  [chain] %-14s rollback_loc=%d pubkey_len=%d" % (name, loc, pklen))
        elif tag == 3 and not hashes_only:  # kernel cmdline
            flags, ln = struct.unpack(">II", payload[0:8])
            print("  [cmdline] flags=%d %r" % (flags, payload[8:8 + ln].decode()))
        elif tag not in (0, 1, 2, 3, 4):
            print("  [tag %d] len=%d" % (tag, len(payload)))


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify vbmeta hash descriptors against shipped images.")
    ap.add_argument("--pkg", required=True, help="extracted package dir containing images/")
    args = ap.parse_args()
    walk_descriptors(args.pkg, "vbmeta.img")
    print()
    vs = os.path.join(args.pkg, "images", "vbmeta_system.img")
    if os.path.exists(vs):
        walk_descriptors(args.pkg, "vbmeta_system.img", hashes_only=True)


if __name__ == "__main__":
    main()
