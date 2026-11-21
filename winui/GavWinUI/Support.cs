using System.Globalization;

namespace GavWinUI;

/// <summary>Finds the GAV folder (lng.ltf + signature databases) and the GavCore engine.</summary>
internal static class GavLocator
{
    public static string? FindGavDir()
    {
        var fromEnv = Environment.GetEnvironmentVariable("GAV_HOME");
        if (!string.IsNullOrWhiteSpace(fromEnv) && File.Exists(Path.Combine(fromEnv, "lng.ltf")))
        {
            return Path.GetFullPath(fromEnv);
        }

        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir is not null; dir = dir.Parent)
        {
            if (File.Exists(Path.Combine(dir.FullName, "lng.ltf")))
            {
                return dir.FullName;
            }
        }

        return null;
    }

    public static string? FindEngine(string? gavDir)
    {
        var candidates = new List<string?>
        {
            Environment.GetEnvironmentVariable("GAVCORE"),
            Path.Combine(AppContext.BaseDirectory, "gavcore.exe"),
        };
        if (gavDir is not null)
        {
            candidates.Add(Path.Combine(gavDir, "GavCore", "build", "Release", "gavcore.exe"));
            candidates.Add(Path.Combine(gavDir, "GavCore", "build", "gavcore.exe"));
            candidates.Add(Path.Combine(gavDir, "gavcore.exe"));
        }
        return candidates.FirstOrDefault(p => !string.IsNullOrWhiteSpace(p) && File.Exists(p));
    }
}

/// <summary>Reader for GAV's lng.ltf translation file, mirroring lang_loader.py.</summary>
internal sealed class Ltf
{
    private readonly Dictionary<string, Dictionary<string, string>> _data = new(StringComparer.OrdinalIgnoreCase);
    private readonly string _lang;

    private Ltf(string lang)
    {
        _lang = lang;
    }

    public static Ltf Load(string? gavDir, string lang)
    {
        var ltf = new Ltf(lang);
        var path = gavDir is null ? null : Path.Combine(gavDir, "lng.ltf");
        if (path is null || !File.Exists(path))
        {
            return ltf;
        }

        Dictionary<string, string>? current = null;
        foreach (var raw in File.ReadLines(path))
        {
            var line = raw.Trim();
            if (line.StartsWith("[lng=", StringComparison.Ordinal) && line.EndsWith(']'))
            {
                current = new Dictionary<string, string>(StringComparer.Ordinal);
                ltf._data[line[5..^1]] = current;
            }
            else if (current is not null && line.IndexOf('=') is var eq and > 0)
            {
                current[line[..eq].Trim()] = line[(eq + 1)..].Trim();
            }
        }

        return ltf;
    }

    public string this[string key] => Get(key);

    public string Format(string key, params (string Name, object Value)[] args)
    {
        var text = Get(key);
        foreach (var (name, value) in args)
        {
            text = text.Replace("{" + name + "}", Convert.ToString(value, CultureInfo.CurrentCulture));
        }
        return text;
    }

    private string Get(string key)
    {
        if (_data.TryGetValue(_lang, out var lang) && lang.TryGetValue(key, out var text))
        {
            return text;
        }
        if (_data.TryGetValue("en", out var en) && en.TryGetValue(key, out text))
        {
            return text;
        }
        return key;
    }
}
