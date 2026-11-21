using System;
using System.Collections.Generic;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

class IlProbe
{
    static string[] Targets = new string[] { "TryTranslate", "DebugHasLiteral", "get_TableId", "TraceMiss", "TextPostfix", "Sweep" };

    static int Main(string[] args)
    {
        try { Console.OutputEncoding = System.Text.Encoding.UTF8; } catch { }
        if (args.Length < 1) { Console.Error.WriteLine("usage: ilprobe <dll> [--scan <needle>] [--full] [--enum <name>] [--callref <name>]"); return 2; }
        string needle = null;
        bool full = false;
        string enumName = null;
        string callRef = null;
        string typeName = null;
        int i = 1;
        while (i < args.Length)
        {
            if (args[i] == "--scan" && i + 1 < args.Length) { needle = args[i + 1]; i += 2; continue; }
            if (args[i] == "--full") { full = true; i++; continue; }
            if (args[i] == "--enum" && i + 1 < args.Length) { enumName = args[i + 1]; i += 2; continue; }
            if (args[i] == "--callref" && i + 1 < args.Length) { callRef = args[i + 1]; i += 2; continue; }
            if (args[i] == "--type" && i + 1 < args.Length) { typeName = args[i + 1]; i += 2; continue; }
            i++;
        }
        AssemblyDefinition asm;
        try { asm = AssemblyDefinition.ReadAssembly(args[0]); }
        catch (Exception e) { Console.WriteLine("LOAD-FAIL " + e.Message); return 3; }

        if (enumName != null)
        {
            var et = FindType(asm, enumName);
            if (et == null) { Console.WriteLine("ENUM-NOT-FOUND " + enumName); }
            else
            {
                foreach (var f in et.Fields)
                    Console.WriteLine("ENUM-FIELD " + f.Name + " = " + Safe(f.Constant));
            }
        }
        if (callRef != null)
        {
            foreach (var t in asm.MainModule.GetTypes())
                foreach (var c in AllTypes(t))
                    CallrefType(c, callRef);
        }
        if (needle != null)
        {
            foreach (var t in asm.MainModule.GetTypes())
                foreach (var c in AllTypes(t))
                    ScanType(c, needle, full);
        }
        if (typeName != null)
        {
            var tt = FindType(asm, typeName);
            if (tt == null) { Console.WriteLine("TYPE-NOT-FOUND " + typeName); }
            else
            {
                foreach (var m in AllMethods(tt))
                    DumpMethod(m);
            }
        }
        if (enumName == null && callRef == null && needle == null && typeName == null)
        {
            foreach (var t in asm.MainModule.GetTypes())
                DumpType(t);
        }
        GC.KeepAlive(asm);
        return 0;
    }

    static IEnumerable<TypeDefinition> AllTypes(TypeDefinition root)
    {
        yield return root;
        foreach (var n in root.NestedTypes)
            foreach (var d in AllTypes(n))
                yield return d;
    }

    static TypeDefinition FindType(AssemblyDefinition asm, string name)
    {
        foreach (var t in asm.MainModule.GetTypes())
            foreach (var c in AllTypes(t))
                if (c.Name == name) return c;
        return null;
    }

    static IEnumerable<MethodDefinition> AllMethods(TypeDefinition root)
    {
        foreach (var m in root.Methods)
            yield return m;
    }

    static void DumpMethod(MethodDefinition m)
    {
        Console.WriteLine("=== IL " + Safe(m).Replace("\n", " ") + " ===");
        try { foreach (var ins in m.Body.Instructions) Console.WriteLine("  " + Instr(ins)); }
        catch (Exception e) { Console.WriteLine("  <dump-fail " + e.Message + ">"); }
    }

    static void CallrefType(TypeDefinition t, string methodName)
    {
        foreach (var m in t.Methods)
        {
            if (!m.HasBody) continue;
            try
            {
                foreach (var ins in m.Body.Instructions)
                {
                    var op = ins.Operand;
                    string on = null;
                    if (op is MethodReference mr) on = mr.Name;
                    else if (op is MethodDefinition md2) on = md2.Name;
                    if (on == methodName)
                        Console.WriteLine("CALLREF " + Safe(t) + "::" + m.Name + " calls -> " + Safe(op));
                }
            }
            catch (Exception e) { Console.WriteLine("<callref-fail " + e.Message + ">"); }
        }
    }

    static void ScanType(TypeDefinition t, string needle, bool full)
    {
        foreach (var m in t.Methods)
        {
            if (!m.HasBody) continue;
            try
            {
                bool hit = false;
                string methodSig = Safe(t) + "::" + Safe(m);
                foreach (var ins in m.Body.Instructions)
                {
                    if (ins.Operand is string s && s.IndexOf(needle, StringComparison.Ordinal) >= 0)
                    {
                        hit = true;
                        Console.WriteLine("HIT " + methodSig.Replace("\n", "\\n") + " :: '" + s.Replace("\n", "\\n") + "'");
                        break;
                    }
                }
                if (hit && full) { Console.WriteLine("=== IL " + Safe(m).Replace("\n"," ") + " ==="); foreach (var ins in m.Body.Instructions) Console.WriteLine("  " + Instr(ins)); }
            }
            catch (Exception e) { Console.WriteLine("<scan-fail " + e.Message + ">"); }
        }
    }

    static void DumpType(TypeDefinition t)
    {
        Console.WriteLine("TYPE " + Safe(t));
        foreach (var m in t.Methods)
            Console.WriteLine("  M " + m.Name + " hasBody=" + m.HasBody);
        foreach (var target in Targets)
        {
            var m = t.Methods.FirstOrDefault(x => x.Name == target);
            if (m == null || !m.HasBody) continue;
            Console.WriteLine("=== IL " + m.Name + " ===");
            try
            {
                foreach (var i in m.Body.Instructions)
                    Console.WriteLine("  " + Instr(i));
            }
            catch (Exception e) { Console.WriteLine("  <dump-fail " + e.Message + ">"); }
        }
    }

    static string Safe(object o)
    {
        try { return o.ToString(); } catch { return "<tosig-fail>"; }
    }

    static string Instr(Instruction i)
    {
        var s = i.OpCode.Name;
        if (i.Operand is MethodReference mr) s += " -> " + Safe(mr);
        else if (i.Operand is FieldReference fr) s += " -> " + Safe(fr);
        else if (i.Operand is string str) s += " '" + str.Replace("\n", "\\n") + "'";
        else if (i.Operand != null) s += " (" + i.Operand.GetType().Name + ")";
        return s;
    }
}
