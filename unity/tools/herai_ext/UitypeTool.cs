using AssetsTools.NET;
using AssetsTools.NET.Extra;
using AssetsTools.NET.Cpp2IL;
using System.Text;

// uitype: read-only inspector + numeric field setter for Unity .assets bundles.
// Built on AssetsTools.NET 3.0.5 (same core ATN herai uses). No Mono/Cpp2IL generator needed
// because the fields we touch (Text, ContentSizeFitter, RectTransform) are built-in Unity types
// resolved from classdata.tpk.

internal static class UitypeTool
{
    // Interest: field names whose current value we want to surface in scans.
    static readonly string[] ScanKeys = new[]
    {
        "m_HorizontalFit", "m_VerticalFit",           // ContentSizeFitter
        "m_Text", "m_FontSize", "m_HorizontalOverflow","m_VerticalOverflow","m_RaycastTarget","m_ResizeActiveForTextPerf","m_AlignViaGeometry","m_AutoSize"
    };

    static AssetsManager MakeManager(string classdataPath, string managedPath)
    {
        var m = new AssetsManager();
        m.LoadClassPackage(classdataPath);
        if (!string.IsNullOrEmpty(managedPath) && Directory.Exists(managedPath))
        {
            m.MonoTempGenerator = new MonoCecilTempGenerator(managedPath);
            Console.Error.WriteLine($"[uitype] Mono support: {managedPath}");
        }
        else Console.Error.WriteLine("[uitype] WARNING: no Managed/ folder found - script fields will be hidden");
        return m;
    }

    static string FindManaged(string startDir)
    {
        var dir = startDir;
        while (dir != null)
        {
            var mdir = Path.Combine(dir, "Managed");
            if (Directory.Exists(mdir)) return mdir;
            foreach (var d in Directory.GetDirectories(dir, "*_Data"))
            {
                var dm = Path.Combine(d, "Managed");
                if (Directory.Exists(dm)) return dm;
            }
            dir = Path.GetDirectoryName(dir);
        }
        return null;
    }

    static string Classdata()
    {
        var baseDir = AppDomain.CurrentDomain.BaseDirectory;
        var p = Path.Combine(baseDir, "classdata.tpk");
        if (File.Exists(p)) return p;
        return Path.GetFullPath("classdata.tpk");
    }

    static void Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine("uitype tree <file> <pathId>          - dump full field tree of one asset");
            Console.Error.WriteLine("uitype scan <file> [nameFilter]      - list Text/ContentSizeFitter components + key fields");
            Environment.Exit(1);
        }

        string cmd = args[0];
        string file = args[1];
        if (!File.Exists(file)) { Console.Error.WriteLine($"not found: {file}"); Environment.Exit(2); }
        var managedPath = FindManaged(Path.GetDirectoryName(Path.GetFullPath(file)));
        var manager = MakeManager(Classdata(), managedPath);

        var inst = manager.LoadAssetsFile(file, true);
        try
        {
            var afile = inst.file;
            manager.LoadClassDatabaseFromPackage(afile.Metadata.UnityVersion);
            Console.Error.WriteLine($"[uitype] {Path.GetFileName(file)} unity={afile.Metadata.UnityVersion}");

            if (cmd == "tree")
            {
                long pathId = long.Parse(args[2]);
                var info = FindByPathId(afile, pathId);
                if (info == null) { Console.Error.WriteLine($"no asset at pathId {pathId}"); return; }
                var bf = manager.GetBaseField(inst, info);
                Console.Error.WriteLine($"=== tree pathId={info.PathId} type={info.TypeId} ===");
                Walk(bf, "", 0);
            }
            else if (cmd == "scan")
            {
                string filter = args.Length > 2 ? args[2] : null;
                Scan(afile, inst, manager, filter);
            }
            else if (cmd == "plan")
            {
                string outTsv = args.Length > 2 ? args[2] : null;
                var enToJp = LoadPairs();
                Plan(afile, inst, manager, enToJp, outTsv);
            }
            else if (cmd == "mtext")
            {
                string outTsv = args.Length > 2 ? args[2] : null;
                MText(afile, inst, manager, outTsv);
            }
            else if (cmd == "layout")
            {
                string outTsv = args.Length > 2 ? args[2] : null;
                Layout(afile, inst, manager, outTsv);
            }
            else if (cmd == "setrect")
            {
                string tsv = args.Length > 2 ? args[2] : null;
                SetRect(afile, inst, manager, file, tsv);
            }
            else if (cmd == "setstr")
            {
                string tsv = args.Length > 2 ? args[2] : null;
                SetStr(afile, inst, manager, file, tsv);
            }
            else if (cmd == "scen")
            {
                string tsv = args.Length > 2 ? args[2] : null;
                bool apply = args.Length > 3 && args[3] == "--apply";
                Scen(afile, inst, manager, file, tsv, apply);
            }
            else if (cmd == "scenjp")
            {
                ScenJp(afile, inst, manager);
            }
            else if (cmd == "scendump")
            {
                string outDir = args.Length > 2 ? args[2] : null;
                ScenDump(afile, inst, manager, outDir);
            }
            else if (cmd == "listgo")
            {
                string flt = args.Length > 2 ? args[2] : null;
                ListGo(afile, inst, manager, flt);
            }
            else if (cmd == "monofields")
            {
                string flt = args.Length > 2 ? args[2] : null;
                MonoFields(afile, inst, manager, flt);
            }
            else if (cmd == "findref")
            {
                long tgt = long.TryParse(args.Length > 2 ? args[2] : null, out var tv) ? tv : -1;
                FindRef(afile, inst, manager, tgt);
            }
            else if (cmd == "findbytes")
            {
                string needle = args.Length > 2 ? args[2] : "scenarioId,lineId,speaker,message";
                FindBytes(afile, inst, manager, needle);
            }
            else if (cmd == "fields")
            {
                string sub = args.Length > 2 ? args[2] : "";
                Fields(afile, inst, manager, sub);
            }
            else if (cmd == "dump")
            {
                long pid = args.Length > 2 ? long.Parse(args[2]) : -1;
                DumpAsset(afile, inst, manager, pid);
            }
            else if (cmd == "api")
            {
                var B = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance;
                Console.Error.WriteLine("--- ATVF props ---");
                foreach (var p in typeof(AssetTypeValueField).GetProperties()) if (!p.Name.StartsWith("Is")) Console.Error.WriteLine($"  {p.PropertyType.Name} {p.Name} {{get={p.CanRead};set={p.CanWrite}}}");
                Console.Error.WriteLine("--- ATVF methods ---");
                foreach (var m in typeof(AssetTypeValueField).GetMethods(B)) Console.Error.WriteLine("  " + m);
                Console.Error.WriteLine("--- AssetsFileWriter ctors+methods ---");
                var wf = typeof(AssetsFileWriter);
                foreach (var c in wf.GetConstructors()) Console.Error.WriteLine("  ctor " + c);
                foreach (var m in wf.GetMethods(B)) Console.Error.WriteLine("  " + m);
                Console.Error.WriteLine("--- AssetFileInfo props+methods ---");
                foreach (var p in typeof(AssetFileInfo).GetProperties()) Console.Error.WriteLine($"  {p.PropertyType.Name} {p.Name} {{get={p.CanRead};set={p.CanWrite}}}");
                foreach (var m in typeof(AssetFileInfo).GetMethods(B)) if (!m.Name.StartsWith("get_")&&!m.Name.StartsWith("set_")&&m.Name!="GetType"&&m.Name!="ToString"&&m.Name!="Equals"&&m.Name!="GetHashCode") Console.Error.WriteLine("  " + m);
                Console.Error.WriteLine("--- AssetsFile all ---");
                foreach (var m in typeof(AssetsFile).GetMethods(B)) Console.Error.WriteLine("  " + m);
            }
        }
        finally
        {
            manager.UnloadAssetsFile(inst);
        }
    }

    static AssetFileInfo FindByPathId(AssetsFile afile, long pathId)
    {
        foreach (var t in Enum.GetValues(typeof(AssetClassID)).Cast<AssetClassID>())
        {
            List<AssetFileInfo> infos;
            try { infos = afile.GetAssetsOfType(t).ToList(); } catch { continue; }
            foreach (var info in infos) if (info.PathId == pathId) return info;
        }
        return null;
    }

    static bool Has(AssetTypeValueField f, string name)
    {
        if (f == null) return false;
        var c = f[name];
        return c != null && !c.IsDummy;
    }

    static void Scan(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string filter)
    {
        foreach (var info in afile.GetAssetsOfType(AssetClassID.MonoBehaviour))
        {
            AssetTypeValueField bf;
            try { bf = manager.GetBaseField(inst, info); } catch { continue; }
            if (bf == null || bf.IsDummy) continue;

            bool isCSF = Has(bf, "m_VerticalFit");                    // ContentSizeFitter
            bool isText = Has(bf, "m_Text") && Has(bf, "m_FontSize"); // UI.Text

            if (!isCSF && !isText) continue;
            string tag = isCSF ? "ContentSizeFitter" : "Text";
            if (filter != null && !tag.Contains(filter, StringComparison.OrdinalIgnoreCase)) continue;

            var sb = new StringBuilder();
            sb.Append($"[{tag}] pathId={info.PathId}");
            // surface key scalar fields
            foreach (var c in bf.Children)
            {
                if (c == null || c.IsDummy) continue;
                if (!ScanKeys.Contains(c.FieldName)) continue;
                sb.Append($"  {c.FieldName}={Scalar(c)}");
            }
            Console.WriteLine(sb.ToString());
        }
    }

    static void Walk(AssetTypeValueField f, string path, int depth)
    {
        if (f == null || f.IsDummy) return;
        var tf = f.TemplateField;
        string type = tf?.Type ?? "?";
        bool container = f.Children != null && f.Children.Count > 0;

        if (!container)
        {
            Console.WriteLine($"{new string(' ', depth * 2)}{path} = {Scalar(f)}   ({type})");
            return;
        }

        bool isArray = (tf != null && tf.IsArray) || type == "Array";
        for (int i = 0; i < f.Children.Count; i++)
        {
            var c = f.Children[i];
            if (c == null || c.IsDummy) continue;
            string cp;
            if (string.IsNullOrEmpty(path)) cp = c.FieldName;
            else if (isArray) cp = $"{path}.{i}";
            else cp = $"{path}.{c.FieldName}";
            Walk(c, cp, depth + 1);
        }
    }

    static string Scalar(AssetTypeValueField f)
    {
        var t = f.TemplateField?.Type;
        try
        {
            switch (t)
            {
                case "string": return $"\"{f.AsString}\"";
                case "int": case "uint": case "sbyte": case "byte":
                case "short": case "ushort": return f.AsInt.ToString();
                case "long": case "ulong": return f.AsLong.ToString();
                case "float": return f.AsFloat.ToString("0.###");
                case "double": return f.AsDouble.ToString("0.###");
                case "bool": return f.AsBool ? "true" : "false";
                default:
                    try { return f.AsString; } catch { return ""; }
            }
        }
        catch { return "?"; }
    }

    // ---- auto-height planner ----------------------------------------------------
    static Dictionary<string,string> LoadPairs()
    {
        var map = new Dictionary<string,string>();
        string p = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "pairs.txt");
        if (!File.Exists(p)) p = Path.GetFullPath("pairs.txt");
        if (File.Exists(p))
        {
            foreach (var l in File.ReadAllLines(p))
            {
                int i = l.IndexOf('=');
                if (i <= 0) continue;
                var jp = l.Substring(0, i).Trim();
                var en = l.Substring(i + 1).Trim();
                if (en.Length == 0) continue;
                map.TryAdd(en, jp);
            }
        }
        return map;
    }

    static int EstLines(string s, float w, float fs, float emPerChar)
    {
        if (string.IsNullOrEmpty(s)) return 1;
        if (w <= 0 || fs <= 0) return 1;
        int cpl = Math.Max(1, (int)Math.Floor(w / (fs * emPerChar)));
        int total = 0;
        foreach (var seg in s.Split('\n'))
            total += Math.Max(1, (int)Math.Ceiling(seg.Length / (double)cpl));
        return total;
    }

    static void Plan(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager,
                     Dictionary<string,string> enToJp, string outTsv)
    {
        var rect = new Dictionary<long,(float w,float h,bool fixedX,bool fixedY)>();
        var tmps = new List<(long pathId, AssetTypeValueField bf)>();

        foreach (var t in Enum.GetValues(typeof(AssetClassID)).Cast<AssetClassID>())
        {
            AssetFileInfo[] infos;
            try { infos = afile.GetAssetsOfType(t).ToArray(); } catch { continue; }
            foreach (var info in infos)
            {
                AssetTypeValueField bf;
                try { bf = manager.GetBaseField(inst, info); } catch { continue; }
                if (bf == null || bf.IsDummy) continue;

                if (Has(bf, "m_SizeDelta"))
                {
                    long go = SafeLong(bf["m_GameObject"]["m_PathID"]);
                    float w = SafeFloat(bf["m_SizeDelta"]["x"]);
                    float h = SafeFloat(bf["m_SizeDelta"]["y"]);
                    bool hasA = Has(bf, "m_AnchorMin") && Has(bf, "m_AnchorMax");
                    float amx = 0, amy = 0, axx = 1, axy = 1;
                    if (hasA)
                    {
                        amx = SafeFloat(bf["m_AnchorMin"]["x"]); amy = SafeFloat(bf["m_AnchorMin"]["y"]);
                        axx = SafeFloat(bf["m_AnchorMax"]["x"]); axy = SafeFloat(bf["m_AnchorMax"]["y"]);
                    }
                    bool fX = hasA && Math.Abs(amx - axx) < 1e-4;
                    bool fY = hasA && Math.Abs(amy - axy) < 1e-4;
                    if (go >= 0) rect[go] = (w, h, fX, fY);
                }

                if (Has(bf, "m_text") && Has(bf, "m_fontSize"))
                    tmps.Add((info.PathId, bf));
            }
        }

        var sb = new StringBuilder();
        if (outTsv != null)
            sb.Append("pathId\tgo\tw\th\tfixedX\tfixedY\tfs\tlenEn\tlenJp\tfactor\tproposedH\tdelta\ten\n");

        int nTmp = 0, placeholder = 0, nowrap = 0, noRect = 0, anchoredY = 0, eligible = 0, wouldGrow = 0, noJp = 0;
        foreach (var (pathId, bf) in tmps)
        {
            nTmp++;
            string en = SafeStr(bf["m_text"]);
            float fs = SafeFloat(bf["m_fontSize"]);
            int wrap = SafeInt(bf["m_TextWrappingMode"]); // 1=Normal,0=NoWrap
            long go = SafeLong(bf["m_GameObject"]["m_PathID"]);

            if (string.IsNullOrWhiteSpace(en) || en.Trim() == "New Text") { placeholder++; continue; }
            if (wrap == 0) { nowrap++; continue; }              // single-line label: height isn't the overflow axis
            if (!rect.TryGetValue(go, out var R)) { noRect++; continue; }
            float h = R.h;
            if (!R.fixedY) { anchoredY++; continue; }          // height is anchor-driven -> sizeDelta isn't the lever
            eligible++;

            int lenEn = en.Length;
            bool hasJp = enToJp.TryGetValue(en.Trim(), out var jp);
            float factor = 1f;
            if (hasJp && jp.Length > 0) factor = Math.Min(3f, Math.Max(1f, (float)lenEn / jp.Length));
            else noJp++;

            float proposed = h * factor;
            float delta = proposed - h;
            if (delta > 0.5f) wouldGrow++;

            if (outTsv != null)
                sb.Append($"{pathId}\t{go}\t{R.w:0.##}\t{h:0.##}\t{(R.fixedX?1:0)}\t{(R.fixedY?1:0)}\t{fs:0.##}\t{lenEn}\t{(hasJp?jp.Length:-1)}\t{factor:0.###}\t{proposed:0.##}\t{delta:0.##}\t{en.Replace('\n',' ')}\n");
        }

        if (outTsv != null) File.WriteAllText(outTsv, sb.ToString());
        Console.Error.WriteLine($"[plan] TMP={nTmp} placeholder(skip)={placeholder} nowrap(skip)={nowrap} noRect={noRect} anchoredY(skip)={anchoredY} eligible(fixedY+wrap)={eligible} wouldGrow={wouldGrow} noJp(keptDefault)={noJp}");
    }

    static void MText(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string outTsv)
    {
        var rect = new Dictionary<long,(float w,float h,bool fixedX,bool fixedY)>();
        var tmps = new List<(long pathId, AssetTypeValueField bf)>();
        foreach (var t in Enum.GetValues(typeof(AssetClassID)).Cast<AssetClassID>())
        {
            AssetFileInfo[] infos;
            try { infos = afile.GetAssetsOfType(t).ToArray(); } catch { continue; }
            foreach (var info in infos)
            {
                AssetTypeValueField bf;
                try { bf = manager.GetBaseField(inst, info); } catch { continue; }
                if (bf == null || bf.IsDummy) continue;

                if (Has(bf, "m_SizeDelta"))
                {
                    long go = SafeLong(bf["m_GameObject"]["m_PathID"]);
                    float w = SafeFloat(bf["m_SizeDelta"]["x"]), h = SafeFloat(bf["m_SizeDelta"]["y"]);
                    bool hasA = Has(bf, "m_AnchorMin") && Has(bf, "m_AnchorMax");
                    float amx = 0, amy = 0, axx = 1, axy = 1;
                    if (hasA)
                    {
                        amx = SafeFloat(bf["m_AnchorMin"]["x"]); amy = SafeFloat(bf["m_AnchorMin"]["y"]);
                        axx = SafeFloat(bf["m_AnchorMax"]["x"]); axy = SafeFloat(bf["m_AnchorMax"]["y"]);
                    }
                    bool fX = hasA && Math.Abs(amx - axx) < 1e-4, fY = hasA && Math.Abs(amy - axy) < 1e-4;
                    if (go >= 0) rect[go] = (w, h, fX, fY);
                }

                if (Has(bf, "m_text") && Has(bf, "m_fontSize")) tmps.Add((info.PathId, bf));
            }
        }

        var sb = new StringBuilder();
        if (outTsv != null) sb.Append("pathId\tfs\twrap\tfixedX\tfixedY\tw\th\ttext\n");
        foreach (var (pid, bf) in tmps)
        {
            string text = SafeStr(bf["m_text"]);
            float fs = SafeFloat(bf["m_fontSize"]); int wrap = SafeInt(bf["m_TextWrappingMode"]);
            long go = SafeLong(bf["m_GameObject"]["m_PathID"]);
            if (!rect.TryGetValue(go, out var R)) continue;
            string clean = text.Replace("\r", "").Replace("\t", " ").Replace("\n", "\\n");
            if (outTsv != null) sb.Append($"{pid}\t{fs:0.##}\t{wrap}\t{(R.fixedX?1:0)}\t{(R.fixedY?1:0)}\t{R.w:0.##}\t{R.h:0.##}\t{clean}\n");
        }
        if (outTsv != null) File.WriteAllText(outTsv, sb.ToString());
    }

    // ---- layout/overlap analysis ------------------------------------------------
    // For each TMP text element, report whether it sits inside a LayoutGroup (V/H/Grid)
    // (auto-stacked -> wrapped lines push siblings down, NO overlap) or is fixed-positioned
    // (a wrapped 2nd line can render over the row below). Also surface self ContentSizeFitter.
    static void Layout(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string outTsv)
    {
        var goName = new Dictionary<long, string>();
        foreach (var info in afile.GetAssetsOfType(AssetClassID.GameObject))
        { AssetTypeValueField bf; try { bf = manager.GetBaseField(inst, info); } catch { continue; }
          if (bf == null || bf.IsDummy) continue;
          goName[info.PathId] = SafeStr(bf["m_Name"]); }

        // transform graph
        var t2go = new Dictionary<long, long>();   // transform pid -> its GO pid
        var tFather = new Dictionary<long, long>(); // transform pid -> father transform pid
        foreach (var info in afile.GetAssetsOfType(AssetClassID.Transform))
        { AssetTypeValueField bf; try { bf = manager.GetBaseField(inst, info); } catch { continue; }
          if (bf == null || bf.IsDummy) continue;
          long go = SafeLong(bf["m_GameObject"]["m_PathID"]);
          long fa = SafeLong(bf["m_Father"]["m_PathID"]);
          if (go >= 0) t2go[info.PathId] = go;
          if (fa >= 0) tFather[info.PathId] = fa; }
        var goFather = new Dictionary<long, long>(); // GO pid -> father GO pid
        foreach (var kv in t2go)
            if (tFather.TryGetValue(kv.Key, out var ftf) && t2go.TryGetValue(ftf, out var fgo))
                goFather[kv.Value] = fgo;

        // per-GO component flags
        var goLayout = new Dictionary<long, string>(); // GO -> V/H/G/L (layout group)
        var goCSFv = new Dictionary<long, int>();       // GO -> ContentSizeFitter m_VerticalFit
        foreach (var info in afile.GetAssetsOfType(AssetClassID.MonoBehaviour))
        { AssetTypeValueField bf; try { bf = manager.GetBaseField(inst, info); } catch { continue; }
          if (bf == null || bf.IsDummy) continue;
          long go = SafeLong(bf["m_GameObject"]["m_PathID"]); if (go < 0) continue;
          if (Has(bf, "m_Spacing") && Has(bf, "m_Padding") && Has(bf, "m_IgnoreInactive"))
          { if (Has(bf, "m_ControlHeight")) goLayout[go] = "V"; else if (Has(bf, "m_ControlWidth")) goLayout[go] = "H"; else if (Has(bf, "m_CellSize")) goLayout[go] = "G"; else goLayout[go] = "L"; }
          if (Has(bf, "m_HorizontalFit") && Has(bf, "m_VerticalFit")) goCSFv[go] = SafeInt(bf["m_VerticalFit"]); }

        // build rect keyed by GO (same logic as Plan)
        var rect = new Dictionary<long,(float w,float h,bool fixedX,bool fixedY)>();
        foreach (var t in Enum.GetValues(typeof(AssetClassID)).Cast<AssetClassID>())
        { AssetFileInfo[] infos; try { infos = afile.GetAssetsOfType(t).ToArray(); } catch { continue; }
          foreach (var info in infos)
          { AssetTypeValueField bf; try { bf = manager.GetBaseField(inst, info); } catch { continue; }
            if (bf == null || bf.IsDummy || !Has(bf,"m_SizeDelta")) continue;
            long go = SafeLong(bf["m_GameObject"]["m_PathID"]);
            float w = SafeFloat(bf["m_SizeDelta"]["x"]), h = SafeFloat(bf["m_SizeDelta"]["y"]);
            bool hasA = Has(bf,"m_AnchorMin")&&Has(bf,"m_AnchorMax");
            float amx=0,amy=0,axx=1,axy=1;
            if (hasA){ amx=SafeFloat(bf["m_AnchorMin"]["x"]); amy=SafeFloat(bf["m_AnchorMin"]["y"]); axx=SafeFloat(bf["m_AnchorMax"]["x"]); axy=SafeFloat(bf["m_AnchorMax"]["y"]); }
            bool fX = hasA && Math.Abs(amx-axx)<1e-4, fY = hasA && Math.Abs(amy-axy)<1e-4;
            if (go>=0) rect[go]=(w,h,fX,fY); } }

        string Nearest(long go)
        { long c = go; int guard = 0; while (c > 0 && guard++ < 64) { if (goLayout.TryGetValue(c, out var lt)) return lt; if (goFather.TryGetValue(c, out var f)) c = f; else break; } return "none"; }

        var sb = new StringBuilder();
        int underLG = 0, fixedPos = 0;
        foreach (var info in afile.GetAssetsOfType(AssetClassID.MonoBehaviour))
        { AssetTypeValueField bf; try { bf = manager.GetBaseField(inst, info); } catch { continue; }
          if (bf == null || bf.IsDummy) continue;
          if (!Has(bf, "m_text") || !Has(bf, "m_fontSize")) continue;
          long go = SafeLong(bf["m_GameObject"]["m_PathID"]);
          float fs = SafeFloat(bf["m_fontSize"]); int wrap = SafeInt(bf["m_TextWrappingMode"]);
          rect.TryGetValue(go, out var R); bool fX=R.fixedX, fY=R.fixedY; float h=R.h;
          string nl = Nearest(go); if (nl == "none") fixedPos++; else underLG++;
          int csfv = goCSFv.TryGetValue(go, out var v) ? v : -1;
          goName.TryGetValue(go, out var gn);
          sb.Append($"{info.PathId}\t{gn}\t{wrap}\t{(fY?1:0)}\t{h:0.##}\t{fs:0.##}\t{nl}\t{csfv}\n"); }
        Console.Error.WriteLine($"[layout] textElems={underLG+fixedPos}  underLayoutGroup={underLG}  fixedPositioned={fixedPos}  | layoutGroups={goLayout.Count} csf={goCSFv.Count} fatherLinks={goFather.Count} transforms={t2go.Count}");
        if (outTsv != null) File.WriteAllText(outTsv, sb.ToString());
    }

    static void SetRect(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string filePath, string tsvPath)
    {
        var rectByGo = new Dictionary<long, AssetFileInfo>();
        foreach (var t in Enum.GetValues(typeof(AssetClassID)).Cast<AssetClassID>())
        {
            AssetFileInfo[] infos;
            try { infos = afile.GetAssetsOfType(t).ToArray(); } catch { continue; }
            foreach (var info in infos)
            {
                AssetTypeValueField bf;
                try { bf = manager.GetBaseField(inst, info); } catch { continue; }
                if (bf == null || bf.IsDummy) continue;
                if (Has(bf, "m_SizeDelta"))
                {
                    long go = SafeLong(bf["m_GameObject"]["m_PathID"]);
                    if (go >= 0) rectByGo[go] = info;
                }
            }
        }

        int done = 0;
        foreach (var line in File.ReadLines(tsvPath))
        {
            var parts = line.Trim().Split('\t');
            if (parts.Length < 2 || parts[0] == "tmpPathId") continue;
            long pid = long.Parse(parts[0]);
            float newH = float.Parse(parts[1], System.Globalization.CultureInfo.InvariantCulture);

            AssetTypeValueField bf = null;
            try { var info = afile.GetAssetInfo(pid); bf = manager.GetBaseField(inst, info); } catch { }
            if (bf == null || bf.IsDummy) { Console.Error.WriteLine($"[setrect] NO FIELD pid={pid}"); continue; }
            long go = SafeLong(bf["m_GameObject"]["m_PathID"]);
            if (!rectByGo.TryGetValue(go, out var rinfo)) { Console.Error.WriteLine($"[setrect] NO RECT pid={pid} go={go}"); continue; }

            AssetTypeValueField rb = manager.GetBaseField(inst, rinfo);
            float old = rb["m_SizeDelta"]["y"].AsFloat;
            rb["m_SizeDelta"]["y"].AsFloat = newH;
            rinfo.SetNewData(rb);
            done++;
            Console.Error.WriteLine($"[setrect] pid={pid} m_SizeDelta.y {old:0.##} -> {newH:0.##}");
        }

        string tmpOut = filePath + ".tmp_unitywrite";
        using (var fs = new FileStream(tmpOut, FileMode.Create, FileAccess.Write))
        using (var writer = new AssetsFileWriter(fs))
        {
            afile.Write(writer, 0);
            writer.Flush();
        }
        manager.UnloadAssetsFile(inst);
        File.Copy(tmpOut, filePath, true);
        File.Delete(tmpOut);
        Console.Error.WriteLine($"[setrect] SAVED {done} changes -> {filePath}");
    }

    // setstr: TSV rows "pathId<TAB>fieldPath<TAB>newValue"; sets string fields on one or more assets, saves file.
    static void SetStr(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string filePath, string tsvPath)
    {
        var byPid = new Dictionary<long, List<(string field, string value)>>();
        foreach (var line in File.ReadLines(tsvPath))
        {
            if (line.StartsWith("#") || string.IsNullOrWhiteSpace(line)) continue;
            var parts = line.TrimEnd('\r', '\n').Split('\t');
            if (parts.Length < 3) { Console.Error.WriteLine($"[setstr] bad row: {line}"); Environment.Exit(2); }
            if (!long.TryParse(parts[0], out var pid)) { Console.Error.WriteLine($"[setstr] bad pathId: {line}"); Environment.Exit(2); }
            if (!byPid.TryGetValue(pid, out var list)) { list = []; byPid[pid] = list; }
            list.Add((parts[1], string.Join("\t", parts.Skip(2))));
        }

        int done = 0;
        foreach (var (pid, updates) in byPid)
        {
            AssetTypeValueField bf = null;
            AssetFileInfo ainfo = null;
            try { ainfo = afile.GetAssetInfo(pid); bf = manager.GetBaseField(inst, ainfo); } catch { }
            if (bf == null || bf.IsDummy) { Console.Error.WriteLine($"[setstr] NO FIELD pid={pid}"); Environment.Exit(2); }
            foreach (var (field, value) in updates)
            {
                var target = bf[field];
                if (target == null || target.IsDummy || target.TemplateField?.Type != "string")
                { Console.Error.WriteLine($"[setstr] not a string field: pid={pid} {field}"); Environment.Exit(2); }
                var old = target.AsString;
                target.AsString = value;
                done++;
                Console.Error.WriteLine($"[setstr] pid={pid} {field}: \"{old}\" -> \"{value}\"");
            }
            ainfo.SetNewData(bf);
        }

        string tmpOut = filePath + ".tmp_unitywrite";
        using (var fs = new FileStream(tmpOut, FileMode.Create, FileAccess.Write))
        using (var writer = new AssetsFileWriter(fs))
        {
            afile.Write(writer, 0);
            writer.Flush();
        }
        manager.UnloadAssetsFile(inst);
        File.Copy(tmpOut, filePath, true);
        File.Delete(tmpOut);
        Console.Error.WriteLine($"[setstr] SAVED {done} changes -> {filePath}");
    }

    // ---- scenario TextAsset byte patcher ----------------------------------------
    // Replaces exact JP option bytes -> EN bytes inside every TextAsset whose m_Bytes
    // contains the scenario CSV header. Byte-level (no UTF-8 round-trip) so any non-text
    // framing is untouched; only the matched spans grow/shrink. Dry-run unless --apply.
    static void Scen(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string file, string tsvPath, bool apply)
    {
        if (tsvPath == null) { Console.Error.WriteLine("[scen] need <file> <pairs.tsv> [--apply]"); return; }
        byte[] HDR = Encoding.UTF8.GetBytes("scenarioId,lineId,speaker,message");
        var pairs = new List<(byte[] jp, byte[] en)>();
        foreach (var line in File.ReadLines(tsvPath))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var parts = line.TrimEnd('\r', '\n').Split('\t');
            if (parts.Length < 2) continue;
            pairs.Add((Encoding.UTF8.GetBytes(parts[0]), Encoding.UTF8.GetBytes(parts[1])));
        }

        int textAssets = 0, scenarioBlobs = 0, totalSwaps = 0;
        foreach (var info in afile.GetAssetsOfType(AssetClassID.TextAsset))
        {
            AssetTypeValueField bf;
            try { bf = manager.GetBaseField(inst, info); } catch { continue; }
            if (bf == null || bf.IsDummy) continue;
            var bfield = bf["m_Bytes"];
            if (bfield == null || bfield.IsDummy) bfield = bf["m_Script"];   // TextAsset bytes field name varies by ATN/Unity version
            if (bfield == null || bfield.IsDummy) continue;
            byte[] bytes = bfield.AsByteArray;
            if (bytes == null) continue;
            textAssets++;

            int hdrCount = CountOccurrences(bytes, HDR);
            Console.Error.WriteLine($"[scen] TextAsset pathId={info.PathId} bytes={bytes.Length} scenarioBlocks={hdrCount}");
            if (hdrCount == 0) continue;
            scenarioBlobs++;

            byte[] cur = bytes;
            int swaps = 0;
            foreach (var pr in pairs)
            {
                int n = CountOccurrences(cur, pr.jp);
                if (n > 0) { swaps += n; cur = ReplaceAll(cur, pr.jp, pr.en); }
            }
            totalSwaps += swaps;
            Console.Error.WriteLine($"[scen]   replacements={swaps} newLen={cur.Length} delta={cur.Length - bytes.Length}");

            if (apply)
            {
                bfield.AsByteArray = cur;
                info.SetNewData(bf);
            }
        }

        Console.Error.WriteLine($"[scen] TextAssets={textAssets} scenarioBlobs={scenarioBlobs} totalSwaps={totalSwaps} apply={apply}");
        if (!apply) return;   // dry-run: do NOT write

        string tmpOut = file + ".tmp_unitywrite";
        using (var fs = new FileStream(tmpOut, FileMode.Create, FileAccess.Write))
        using (var writer = new AssetsFileWriter(fs))
        {
            afile.Write(writer, 0);
            writer.Flush();
        }
        manager.UnloadAssetsFile(inst);
        File.Copy(tmpOut, file, true);
        File.Delete(tmpOut);
        Console.Error.WriteLine($"[scen] SAVED -> {file}");
    }

    // ---- read-only JP scan of scenario TextAssets (for verification) --------------
    static void ScenJp(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager)
    {
        byte[] HDR = Encoding.UTF8.GetBytes("scenarioId,lineId,speaker,message");
        int textAssets = 0, scenarioBlobs = 0;
        long totalJp = 0;
        foreach (var info in afile.GetAssetsOfType(AssetClassID.TextAsset))
        {
            AssetTypeValueField bf;
            try { bf = manager.GetBaseField(inst, info); } catch { continue; }
            if (bf == null || bf.IsDummy) continue;
            var bfield = bf["m_Bytes"];
            if (bfield == null || bfield.IsDummy) bfield = bf["m_Script"];
            if (bfield == null || bfield.IsDummy) continue;
            byte[] bytes = bfield.AsByteArray;
            if (bytes == null) continue;
            textAssets++;
            if (CountOccurrences(bytes, HDR) == 0) continue;
            scenarioBlobs++;
            string s = Encoding.UTF8.GetString(bytes);
            var jpIdx = new List<int>();
            for (int i = 0; i < s.Length; i++)
            {
                int code = (int)s[i];
                bool isJp = (code >= 0x3040 && code <= 0x30FF)
                         || (code >= 0x4E00 && code <= 0x9FFF)
                         || (code >= 0x3400 && code <= 0x4DBF)
                         || (code >= 0xF900 && code <= 0xFAFF)
                         || (code >= 0xFF65 && code <= 0xFF9F);
                if (isJp) jpIdx.Add(i);
            }
            totalJp += jpIdx.Count;
            Console.Error.WriteLine($"[scenjp] pathId={info.PathId} bytes={bytes.Length} jpChars={jpIdx.Count}");
            if (jpIdx.Count > 0)
            {
                int shown = 0;
                foreach (var idx in jpIdx)
                {
                    if (shown++ >= 6) break;
                    int a = Math.Max(0, idx - 12), b = Math.Min(s.Length, idx + 12);
                    string ctx = s.Substring(a, b - a).Replace("\n", "\\n").Replace("\r", "");
                    Console.Error.WriteLine($"[scenjp]   U+{(int)s[idx]:X4} ...{ctx}...");
                }
            }
        }
        Console.Error.WriteLine($"[scenjp] TextAssets={textAssets} scenarioBlobs={scenarioBlobs} TOTAL_JP_CHARS={totalJp}");
    }

    // ---- read-only: write each scenario TextAsset to a .csv for inspection --------
    // ---- find MonoBehaviours referencing a given pathId (diagnostic) -------------
    static void FindRef(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, long target)
    {
        foreach (var info in afile.GetAssetsOfType(AssetClassID.MonoBehaviour))
        {
            AssetTypeValueField bf;
            try { bf = manager.GetBaseField(inst, info); } catch { continue; }
            if (bf == null || bf.IsDummy) continue;
            foreach (var c in (bf.Children ?? new List<AssetTypeValueField>()))
            {
                if (c == null || c.IsDummy) continue;
                try { var pf = c["m_PathID"]; if (pf != null && pf.AsInt == target)
                    Console.Error.WriteLine($"[findref] mbPid={info.PathId} field={c.FieldName} -> pathId={target}"); } catch { }
            }
        }
    }

    // ---- find MonoBehaviour fields by name -> referenced pathId (diagnostic) -----
    static void MonoFields(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string filter)
    {
        foreach (var info in afile.GetAssetsOfType(AssetClassID.MonoBehaviour))
        {
            AssetTypeValueField bf;
            try { bf = manager.GetBaseField(inst, info); } catch { continue; }
            if (bf == null || bf.IsDummy) continue;
            foreach (var c in (bf.Children ?? new List<AssetTypeValueField>()))
            {
                if (c == null || c.IsDummy) continue;
                if (filter != null && !c.FieldName.Contains(filter, StringComparison.OrdinalIgnoreCase)) continue;
                long pid = 0; string s = "";
                try { var pf = c["m_PathID"]; if (pf != null) pid = pf.AsInt; } catch { }
                try { s = SafeStr(c); } catch { }
                Console.Error.WriteLine($"[mono] mbPid={info.PathId} field={c.FieldName} -> pathId={pid} str=\"{s}\"");
            }
        }
    }

    // ---- list GameObjects by name (diagnostic) ------------------------------------
    static void ListGo(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string filter)
    {
        foreach (var info in afile.GetAssetsOfType(AssetClassID.GameObject))
        {
            AssetTypeValueField bf;
            try { bf = manager.GetBaseField(inst, info); } catch { continue; }
            if (bf == null || bf.IsDummy) continue;
            string name = SafeStr(bf["m_Name"]);
            if (!string.IsNullOrEmpty(filter) && name.IndexOf(filter, StringComparison.OrdinalIgnoreCase) < 0) continue;
            Console.Error.WriteLine($"[listgo] pid={info.PathId} name=\"{name}\"");
        }
    }

    static void ScenDump(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string outDir)
    {
        byte[] HDR = Encoding.UTF8.GetBytes("scenarioId,lineId,speaker,message");
        foreach (var info in afile.GetAssetsOfType(AssetClassID.TextAsset))
        {
            AssetTypeValueField bf;
            try { bf = manager.GetBaseField(inst, info); } catch { continue; }
            if (bf == null || bf.IsDummy) continue;
            var bfield = bf["m_Bytes"];
            if (bfield == null || bfield.IsDummy) bfield = bf["m_Script"];
            if (bfield == null || bfield.IsDummy) continue;
            byte[] bytes = bfield.AsByteArray;
            if (bytes == null) continue;
            if (CountOccurrences(bytes, HDR) == 0) continue;
            string s = Encoding.UTF8.GetString(bytes);
            string outp = Path.Combine(outDir ?? ".", $"scen_{info.PathId}.csv");
            File.WriteAllText(outp, s);
            Console.Error.WriteLine($"[scendump] pathId={info.PathId} -> {outp} ({bytes.Length} bytes)");
        }
    }

    static int Find(byte[] hay, byte[] needle, int start)
    {
        if (needle.Length == 0) return start;
        for (int i = start; i <= hay.Length - needle.Length; i++)
        {
            bool ok = true;
            for (int j = 0; j < needle.Length; j++)
                if (hay[i + j] != needle[j]) { ok = false; break; }
            if (ok) return i;
        }
        return -1;
    }

    static int CountOccurrences(byte[] hay, byte[] needle)
    {
        if (needle.Length == 0 || hay.Length < needle.Length) return 0;
        int count = 0, i = 0;
        while ((i = Find(hay, needle, i)) >= 0) { count++; i += needle.Length; }
        return count;
    }

    static byte[] ReplaceAll(byte[] src, byte[] from, byte[] to)
    {
        if (from.Length == 0 || CountOccurrences(src, from) == 0) return src;
        var list = new List<byte>();
        int i = 0, last = 0;
        while ((i = Find(src, from, i)) >= 0)
        {
            for (int k = last; k < i; k++) list.Add(src[k]);
            list.AddRange(to);
            i += from.Length; last = i;
        }
        for (int k = last; k < src.Length; k++) list.Add(src[k]);
        return list.ToArray();
    }

    // ---- dump string fields whose name contains a substring (diagnostic) -------
    static void Fields(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string sub)
    {
        foreach (var t in Enum.GetValues(typeof(AssetClassID)).Cast<AssetClassID>())
        {
            List<AssetFileInfo> infos;
            try { infos = afile.GetAssetsOfType(t).ToList(); } catch { continue; }
            foreach (var info in infos)
            {
                AssetTypeValueField bf;
                try { bf = manager.GetBaseField(inst, info); } catch { continue; }
                if (bf == null || bf.IsDummy) continue;
                WalkFields(bf, "", t, info.PathId, sub);
            }
        }
    }

    static void WalkFields(AssetTypeValueField f, string path, AssetClassID type, long pid, string sub)
    {
        if (f == null || f.IsDummy) return;
        string p = string.IsNullOrEmpty(path) ? f.FieldName : path + "." + f.FieldName;
        var tt = f.TemplateField?.Type;
        if (tt == "string" && !string.IsNullOrEmpty(sub) && f.FieldName.IndexOf(sub, StringComparison.OrdinalIgnoreCase) >= 0)
        { try { Console.Error.WriteLine($"[fields] type={type} pid={pid} field={p} val={f.AsString}"); } catch { }
        }
        if (f.Children != null) foreach (var c in f.Children) WalkFields(c, p, type, pid, sub);
    }

    // ---- dump every scalar field of one asset by pathId (diagnostic) -----------
    static void DumpAsset(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, long pid)
    {
        foreach (var t in Enum.GetValues(typeof(AssetClassID)).Cast<AssetClassID>())
        {
            List<AssetFileInfo> infos;
            try { infos = afile.GetAssetsOfType(t).ToList(); } catch { continue; }
            AssetFileInfo match = null;
            foreach (var info in infos) if (info.PathId == pid) { match = info; break; }
            if (match == null) continue;
            AssetTypeValueField bf;
            try { bf = manager.GetBaseField(inst, match); } catch { continue; }
            if (bf == null || bf.IsDummy) continue;
            Console.Error.WriteLine($"[dump] type={t} pathId={pid}");
            DumpField(bf, "");
            return;
        }
        Console.Error.WriteLine($"[dump] pathId={pid} NOT FOUND");
    }

    static void DumpField(AssetTypeValueField f, string path)
    {
        if (f == null || f.IsDummy) return;
        string p = string.IsNullOrEmpty(path) ? f.FieldName : path + "." + f.FieldName;
        var tt = f.TemplateField?.Type;
        if (tt == "string") { try { Console.Error.WriteLine($"  {p} = \"{f.AsString}\""); } catch { }
        } else if (tt == "Object") { try { var o = f.AsObject; if (o != null) Console.Error.WriteLine($"  {p} -> {o.ToString()}"); } catch { }
        } else if (tt != null && tt != "Array" && tt != "byte") { try { Console.Error.WriteLine($"  {p} : ({tt})"); } catch { }
        }
        if (f.Children != null) foreach (var c in f.Children) DumpField(c, p);
    }

    // ---- locate a UTF-8 needle inside any asset field (diagnostic) --------------
    static void FindBytes(AssetsFile afile, AssetsFileInstance inst, AssetsManager manager, string needle)
    {
        byte[] nb = Encoding.UTF8.GetBytes(needle);
        foreach (var t in Enum.GetValues(typeof(AssetClassID)).Cast<AssetClassID>())
        {
            List<AssetFileInfo> infos;
            try { infos = afile.GetAssetsOfType(t).ToList(); } catch { continue; }
            foreach (var info in infos)
            {
                AssetTypeValueField bf;
                try { bf = manager.GetBaseField(inst, info); } catch { continue; }
                if (bf == null || bf.IsDummy) continue;
                SearchField(bf, "", nb, t, info.PathId);
            }
        }
    }

    static void SearchField(AssetTypeValueField f, string path, byte[] nb, AssetClassID type, long pid)
    {
        if (f == null || f.IsDummy) return;
        string p = string.IsNullOrEmpty(path) ? f.FieldName : path + "." + f.FieldName;
        var tt = f.TemplateField?.Type;
        try { if (tt == "string" && f.AsString != null && CountOccurrences(Encoding.UTF8.GetBytes(f.AsString), nb) > 0)
            Console.Error.WriteLine($"[findbytes] STR type={type} pathId={pid} field={p} len={f.AsString.Length}"); } catch { }
        try { byte[] b = f.AsByteArray; if (b != null && CountOccurrences(b, nb) > 0)
            Console.Error.WriteLine($"[findbytes] BYTES type={type} pathId={pid} field={p} len={b.Length} hits={CountOccurrences(b, nb)}"); } catch { }
        if (f.Children != null) foreach (var c in f.Children) SearchField(c, p, nb, type, pid);
    }

    static string SafeStr(AssetTypeValueField f)
    {
        if (f == null || f.IsDummy) return "";
        try { return f.AsString; } catch { return ""; }
    }
    static float SafeFloat(AssetTypeValueField f)
    {
        if (f == null || f.IsDummy) return 0;
        try { return f.AsFloat; } catch { try { return (float)f.AsDouble; } catch { return 0; } }
    }
    static int SafeInt(AssetTypeValueField f)
    {
        if (f == null || f.IsDummy) return 0;
        try { return f.AsInt; } catch { try { return (int)f.AsLong; } catch { return 0; } }
    }
    static long SafeLong(AssetTypeValueField f)
    {
        if (f == null || f.IsDummy) return -1;
        try { return f.AsLong; } catch { return -1; }
    }
}
