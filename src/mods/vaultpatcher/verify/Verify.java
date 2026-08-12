import com.google.gson.*;
import com.ldtteam.structurize.client.gui.WindowExtendedBuildTool;
import me.fengming.vaultpatcher_asm.config.*;
import me.fengming.vaultpatcher_asm.core.utils.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

/** 把「全部 1085 个 key + 命中路径 + 未命中路径」的输出摘成一个哈希，原 jar 与补丁 jar 必须一致 */
public class Verify {
    public static void main(String[] a) throws Exception {
        JsonArray arr = JsonParser.parseString(new String(Files.readAllBytes(Paths.get(a[0])), StandardCharsets.UTF_8)).getAsJsonArray();
        List<String> allKeys = new ArrayList<>();
        for (JsonElement e : arr) {
            JsonObject o = e.getAsJsonObject();
            Pairs p = new Pairs(true);
            for (JsonElement pe : o.getAsJsonArray("p")) {
                JsonArray kv = pe.getAsJsonArray();
                p.setKey(kv.get(0).getAsString());
                p.setValue(kv.get(1).getAsString());
                allKeys.add(kv.get(0).getAsString());
            }
            TargetClassInfo t = new TargetClassInfo();
            t.setDynamicName(o.get("t").getAsString());
            TranslationInfo.Mutable m = new TranslationInfo.Mutable(o.get("t").getAsString());
            Utils.dynTranslationInfos.add(m.setPairs(p).setTargetClassInfo(t).toImmutable());
        }
        Utils.needStacktrace = true;
        Collections.sort(allKeys);

        StringBuilder sb = new StringBuilder();
        int[] hits = new int[2];
        // 命中路径：从 WindowExtendedBuildTool 里调用
        for (String k : allKeys) {
            String r = WindowExtendedBuildTool.call(k);
            if (!r.equals(k)) hits[0]++;
            sb.append("HIT\t").append(k).append('\t').append(r).append('\n');
        }
        // 未命中路径：从本类调用（类名不匹配任何 target_class）
        for (String k : allKeys) {
            String r = DynamicReplaceUtils.__mappingString(k, "x");
            if (!r.equals(k)) hits[1]++;
            sb.append("MISS\t").append(k).append('\t').append(r).append('\n');
        }
        for (String k : new String[]{"FPS: 60", "钻石镐", "", "  ", "Nonexistent String 12345"})
            sb.append("EXTRA\t").append(k).append('\t')
              .append(DynamicReplaceUtils.__mappingString(k, "x")).append('\n');

        byte[] h = MessageDigest.getInstance("SHA-256").digest(sb.toString().getBytes(StandardCharsets.UTF_8));
        StringBuilder hex = new StringBuilder();
        for (byte b : h) hex.append(String.format("%02x", b));
        System.out.println("keys=" + allKeys.size() + "  命中并被替换=" + hits[0]
                + "  未命中被替换=" + hits[1] + "  输出摘要=" + hex);
    }
}
