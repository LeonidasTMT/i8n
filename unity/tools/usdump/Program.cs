using System;
using System.Collections.Generic;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// modes:
//   usdump <dll> fields <f1,f2,...>   -> dump methods whose IL touches listed field names (any type)
//   usdump <dll> exact  <s1> [s2 ...] -> dump methods with Ldstr exactly equal (raw or \uXXXX-escaped input)
string dll = args[0];
var mode = args.Length > 1 ? args[1] : "";

HashSet<string> fieldNames = new();
HashSet<string> exactStrings = new();
if (mode == "fields") { foreach (var f in args.Skip(2)) foreach (var n in f.Split(',')) if (n != "") fieldNames.Add(n); }
else if (mode == "exact") { foreach (var s in args.Skip(2)) exactStrings.Add(Unesc(s)); }

string Unesc(string s)
{
    var sb = new System.Text.StringBuilder();
    for (int i = 0; i < s.Length; i++)
    {
        if (s[i] == '\\' && i + 5 <= s.Length && s[i + 1] == 'u')
        { sb.Append((char)int.Parse(s.Substring(i + 2, 4), System.Globalization.NumberStyles.HexNumber)); i += 5; }
        else sb.Append(s[i]);
    }
    return sb.ToString();
}

var asm = AssemblyDefinition.ReadAssembly(dll);
foreach (var mod in asm.Modules)
foreach (var type in mod.GetTypes())
{
    foreach (var m in AllMethods(type))
    {
        if (m.Body == null) continue;
        bool fieldHit = false, exactHit = false;
        var hitStrs = new List<string>();
        foreach (var inst in m.Body.Instructions)
        {
            if (inst.OpCode.Code == Code.Ldstr && inst.Operand is string s2)
            {
                if (exactStrings.Contains(s2)) { exactHit = true; hitStrs.Add(Esc(s2)); }
            }
            else if ((inst.OpCode.Code == Code.Ldfld || inst.OpCode.Code == Code.Stfld || inst.OpCode.Code == Code.Ldflda)
                     && inst.Operand is FieldReference fr && fieldNames.Contains(fr.Name)) fieldHit = true;
        }
        if (fieldHit || exactHit)
        {
            Console.WriteLine($"METHOD {(exactHit ? "[EXACT:" + string.Join(" | ", hitStrs) + "] " : "")}{(fieldHit ? "[FIELD]" : "")} {type.FullName}::{m.Name}");
            int i = 0;
            foreach (var inst in m.Body.Instructions)
            {
                var op = "";
                if (inst.OpCode.Code == Code.Ldstr && inst.Operand is string s3) op = "ldstr " + Esc(s3);
                else if (inst.OpCode.Code == Code.Ldc_I4 && inst.Operand is int iv) op = $"ldc.i4 {iv}";
                else if (inst.OpCode.Code == Code.Callvirt || inst.OpCode.Code == Code.Call || inst.OpCode.Code == Code.Newobj || inst.OpCode.Code == Code.Ldftn) op = $"{inst.OpCode} {(MethodReference)inst.Operand}";
                else if (inst.Operand is FieldReference fr2) op = $"{inst.OpCode} {fr2.Name}";
                else if (inst.Operand != null) op = $"{inst.OpCode} {inst.Operand.GetType().Name}";
                else op = inst.OpCode.ToString();
                Console.WriteLine($"  [{i}] {op}");
                i++;
            }
        }
    }
}
static string Esc(string s)
{
    var sb = new System.Text.StringBuilder();
    foreach (var c in s)
        sb.Append(c < 0x20 || c > 0x7e ? "\\u" + ((int)c).ToString("x4") : c.ToString());
    return sb.ToString();
}
static IEnumerable<MethodDefinition> AllMethods(TypeDefinition t)
{
    var list = new List<MethodDefinition>();
    try { foreach (var m in t.Methods) list.Add(m); } catch { }
    try { foreach (var n in t.NestedTypes) foreach (var m in n.Methods) list.Add(m); } catch { }
    return list;
}
