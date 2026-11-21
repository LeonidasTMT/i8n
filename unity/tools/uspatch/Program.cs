using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Mono.Cecil;
using Mono.Cecil.Cil;

// usage: uspatch <in.dll> <out.dll> <map.json> [report.tsv] [--trace trace.json]
if (args.Length < 3)
{
    Console.Error.WriteLine("usage: uspatch <in.dll> <out.dll> <map.json> [report.tsv]");
    return 2;
}

string inPath = args[0];
string outPath = args[1];
string mapPath = args[2];
string reportPath = args.Length >= 4 && !args[3].StartsWith("--") ? args[3] : null;
string tracePath = null;
for (int i = 0; i + 1 < args.Length; i++)
    if (args[i] == "--trace") tracePath = args[i + 1];

var map = LoadMap(File.ReadAllText(mapPath));
Console.Error.WriteLine($"[uspatch] map keys={map.Count}");

var asm = AssemblyDefinition.ReadAssembly(inPath);
int replaced = 0;
var hitKeys = new HashSet<string>();
var lines = new List<string>();
var trace = new List<object>();
int seq = 0;

foreach (var mod in asm.Modules)
{
    foreach (var type in mod.GetTypes())
    {
        foreach (var m in AllMethods(type))
        {
            if (m.Body == null) continue;
            foreach (var inst in m.Body.Instructions)
            {
                if (inst.OpCode.Code == Code.Ldstr && inst.Operand is string s)
                {
                    int idx = seq++;
                    string key = s.Trim();
                    bool hit = map.TryGetValue(key, out string en) && !string.IsNullOrEmpty(en);
                    if (hit)
                    {
                        inst.Operand = en;
                        replaced++;
                        hitKeys.Add(key);
                        lines.Add(s.Replace("\t", " ") + "\t=>\t" + en.Replace("\r", "").Replace("\n", "\\n"));
                    }
                    trace.Add(new { i = idx, v = s, hit });
                }
            }
        }
    }
}

asm.Write(outPath);
Console.Error.WriteLine($"[uspatch] replaced={replaced} unique_keys_hit={hitKeys.Count}");
if (reportPath != null) File.WriteAllLines(reportPath, lines);
if (tracePath != null) File.WriteAllText(tracePath, JsonSerializer.Serialize(trace));
return 0;

static Dictionary<string, string> LoadMap(string raw)
{
    var d = new Dictionary<string, string>();
    using var doc = JsonDocument.Parse(raw);
    foreach (var p in doc.RootElement.EnumerateObject())
        d[p.Name] = p.Value.GetString() ?? "";
    return d;
}

static IEnumerable<MethodDefinition> AllMethods(TypeDefinition t)
{
    var list = new List<MethodDefinition>();
    try { foreach (var m in t.Methods) list.Add(m); } catch { }
    try { foreach (var n in t.NestedTypes) foreach (var m in n.Methods) list.Add(m); } catch { }
    return list;
}
