package com.ldtteam.structurize.client.gui;
import me.fengming.vaultpatcher_asm.core.utils.DynamicReplaceUtils;
/** 名字必须与 minecolonies_styles.json 的 target_class 完全一致，才能走到「命中」分支 */
public class WindowExtendedBuildTool {
    public static String call(String s) { return DynamicReplaceUtils.__mappingString(s, "onOpened"); }
}
