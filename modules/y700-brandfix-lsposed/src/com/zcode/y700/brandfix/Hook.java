package com.zcode.y700.brandfix;

import android.os.Build;
import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

/**
 * Spoofs Build.BRAND / Build.MANUFACTURER to "OnePlus" only inside
 * heytap / ColorOS / Oplus AI processes (scope is additionally limited by
 * LSPosed per-app scope). Fixes XiaoBu's BrandEnvActivity rejecting the
 * device while the main identity stays Lenovo-TB322FC for WeChat and
 * per-model game graphics profiles.
 */
public class Hook implements IXposedHookLoadPackage {
    private static final String[] PREFIXES = {
        "com.heytap.", "com.coloros.", "com.oplus.", "com.aiunit."
    };

    @Override
    public void handleLoadPackage(XC_LoadPackage.LoadPackageParam lpparam) throws Throwable {
        String pkg = lpparam.packageName;
        boolean target = false;
        for (String p : PREFIXES) {
            if (pkg != null && pkg.startsWith(p)) { target = true; break; }
        }
        if (!target) return;
        try {
            XposedHelpers.setStaticObjectField(Build.class, "BRAND", "OnePlus");
            XposedHelpers.setStaticObjectField(Build.class, "MANUFACTURER", "OnePlus");
            XposedBridge.log("Y700BrandFix: spoofed brand/manufacturer=OnePlus for " + pkg);
        } catch (Throwable t) {
            XposedBridge.log("Y700BrandFix: failed for " + pkg + ": " + t);
        }
    }
}
