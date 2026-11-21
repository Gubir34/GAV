using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.Text;
using System.Text.Json;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;
using Windows.Storage.Pickers;
using Windows.System;

namespace GavWinUI;

public sealed class ResultItem
{
    public ResultItem(string title, string detail, string glyph)
    {
        Title = title;
        Detail = detail;
        Glyph = glyph;
    }

    public string Title { get; }
    public string Detail { get; }
    public string Glyph { get; }
}

public sealed partial class MainWindow : Window
{
    private const string ThreatGlyph = "\uE7BA";
    private const string ErrorGlyph = "\uE897";

    private readonly ObservableCollection<ResultItem> _threats = new();
    private readonly ObservableCollection<ResultItem> _errors = new();
    private readonly string? _gavDir = GavLocator.FindGavDir();
    private readonly string? _engine = GavLocator.FindEngine(GavLocator.FindGavDir());
    private readonly Ltf _t;
    private CancellationTokenSource? _cts;
    private bool _finished;

    public MainWindow()
    {
        InitializeComponent();
        _t = Ltf.Load(_gavDir, CultureInfo.CurrentUICulture.TwoLetterISOLanguageName);

        Title = _t["gui_title"];
        AppWindow.Resize(new Windows.Graphics.SizeInt32(960, 680));
        PathBox.PlaceholderText = _t["gui_path_placeholder"];
        BrowseButton.Content = _t["gui_choose"];
        ThreatList.ItemsSource = _threats;
        ErrorList.ItemsSource = _errors;
        UpdateHeaders();
        SetBusy(false);
        ProgressText.Text = _t["gui_ready"];

        if (_gavDir is null || _engine is null)
        {
            ShowStatus(InfoBarSeverity.Error, _gavDir is null
                ? "GAV folder (lng.ltf) not found. Set GAV_HOME to the GAV folder."
                : "gavcore.exe not found. Run: py install_gavcore.py");
            ScanButton.IsEnabled = false;
        }
        else
        {
            ShowStatus(InfoBarSeverity.Informational, _t["gui_ready"]);
            var args = Environment.GetCommandLineArgs();
            if (args.Length > 1)
            {
                PathBox.Text = args[1];
            }
        }
    }

    private async void Browse_Click(object sender, RoutedEventArgs e)
    {
        var picker = new FolderPicker { SuggestedStartLocation = PickerLocationId.ComputerFolder };
        picker.FileTypeFilter.Add("*");
        WinRT.Interop.InitializeWithWindow.Initialize(picker, WinRT.Interop.WindowNative.GetWindowHandle(this));
        var folder = await picker.PickSingleFolderAsync();
        if (folder is not null)
        {
            PathBox.Text = folder.Path;
        }
    }

    private void PathBox_KeyDown(object sender, KeyRoutedEventArgs e)
    {
        if (e.Key == VirtualKey.Enter && _cts is null)
        {
            Scan_Click(sender, e);
        }
    }

    private async void Scan_Click(object sender, RoutedEventArgs e)
    {
        if (_cts is not null)
        {
            _cts.Cancel();
            ScanButton.IsEnabled = false;
            return;
        }

        var path = PathBox.Text.Trim();
        if (_gavDir is null || _engine is null || path.Length == 0 || !(Directory.Exists(path) || File.Exists(path)))
        {
            ShowStatus(InfoBarSeverity.Error, _t.Format("gui_invalid_path", ("path", path)));
            return;
        }

        _threats.Clear();
        _errors.Clear();
        UpdateHeaders();
        _finished = false;
        _cts = new CancellationTokenSource();
        SetBusy(true);
        ProgressText.Text = _t["gui_collecting"];
        ShowStatus(InfoBarSeverity.Informational, _t["gui_collecting"]);

        try
        {
            await RunScanAsync(path, _cts.Token);
        }
        catch (Exception ex)
        {
            ShowStatus(InfoBarSeverity.Error, ex.Message);
        }
        finally
        {
            _cts.Dispose();
            _cts = null;
            SetBusy(false);
        }
    }

    private async Task RunScanAsync(string target, CancellationToken ct)
    {
        using var process = StartEngine(target);
        using var registration = ct.Register(() =>
        {
            try
            {
                if (!process.HasExited)
                {
                    process.Kill(entireProcessTree: true);
                }
            }
            catch (Exception ex) when (ex is InvalidOperationException or Win32Exception)
            {
                // Already exited.
            }
        });

        var stderrTask = process.StandardError.ReadToEndAsync();
        string? line;
        while ((line = await process.StandardOutput.ReadLineAsync()) is not null)
        {
            HandleEvent(line);
        }

        var stderr = await stderrTask;
        await process.WaitForExitAsync();

        if (ct.IsCancellationRequested)
        {
            ProgressText.Text = _t["gui_cancelled"];
            ShowStatus(InfoBarSeverity.Warning, _t["gui_cancelled"]);
        }
        else if (!_finished)
        {
            var message = stderr.Trim();
            ShowStatus(InfoBarSeverity.Error, message.Length > 0 ? message : $"Scanner exited with code {process.ExitCode}");
        }
    }

    private Process StartEngine(string target)
    {
        var psi = new ProcessStartInfo(_engine!)
        {
            WorkingDirectory = _gavDir!,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
        };
        psi.ArgumentList.Add("--db-dir");
        psi.ArgumentList.Add(_gavDir!);
        psi.ArgumentList.Add("--json");
        psi.ArgumentList.Add("--");
        psi.ArgumentList.Add(target);
        return Process.Start(psi) ?? throw new InvalidOperationException("Could not start gavcore.exe");
    }

    // File names can carry bidi overrides (e.g. "invoice\u202Egpj.exe") or control characters: show them escaped.
    private static string Display(string text)
    {
        var sb = new StringBuilder(text.Length);
        foreach (var c in text)
        {
            var category = CharUnicodeInfo.GetUnicodeCategory(c);
            if (char.IsControl(c) || category == UnicodeCategory.Format)
            {
                sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
            }
            else
            {
                sb.Append(c);
            }
        }
        return sb.ToString();
    }

    private void HandleEvent(string line)
    {
        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(line);
        }
        catch (JsonException)
        {
            return;
        }

        using (doc)
        {
            var ev = doc.RootElement;
            switch (ev.GetProperty("type").GetString())
            {
                case "start":
                    SetProgress(0, ev.GetProperty("total").GetInt32());
                    break;
                case "progress":
                    SetProgress(ev.GetProperty("done").GetInt32(), ev.GetProperty("total").GetInt32());
                    break;
                case "threat":
                    _threats.Add(new ResultItem(
                        Display(ev.GetProperty("path").GetString() ?? ""),
                        $"{ev.GetProperty("algo").GetString()}  {ev.GetProperty("hash").GetString()}",
                        ThreatGlyph));
                    UpdateHeaders();
                    ResultPivot.SelectedIndex = 0;
                    break;
                case "error":
                    _errors.Add(new ResultItem(
                        Display(ev.GetProperty("path").GetString() ?? ""),
                        ev.GetProperty("reason").GetString() ?? "",
                        ErrorGlyph));
                    UpdateHeaders();
                    break;
                case "fatal":
                    _finished = true;
                    ProgressText.Text = _t["gui_ready"];
                    var message = ev.GetProperty("message").GetString() ?? "";
                    ShowStatus(InfoBarSeverity.Error,
                        message.StartsWith("No signatures", StringComparison.Ordinal) ? _t["gui_no_signatures"] : message);
                    break;
                case "done":
                    if (ev.TryGetProperty("cancelled", out var c) && c.GetBoolean())
                    {
                        break;  // reported by RunScanAsync
                    }
                    _finished = true;
                    var threats = ev.GetProperty("threats").GetInt32();
                    Progress.IsIndeterminate = false;
                    Progress.Value = 1;
                    ProgressText.Text = _t["scan_done"].Trim('-');
                    ShowStatus(threats > 0 ? InfoBarSeverity.Error : InfoBarSeverity.Success, _t.Format("gui_summary",
                        ("scanned", ev.GetProperty("scanned").GetInt32()),
                        ("total", ev.GetProperty("total").GetInt32()),
                        ("threats", threats),
                        ("errors", ev.GetProperty("errors").GetInt32()),
                        ("elapsed", ev.GetProperty("elapsed").GetDouble().ToString("0.0", CultureInfo.CurrentCulture))));
                    break;
            }
        }
    }

    private void SetProgress(int done, int total)
    {
        Progress.IsIndeterminate = false;
        Progress.Value = total == 0 ? 1 : (double)done / total;
        ProgressText.Text = _t.Format("gui_progress", ("done", done), ("total", total));
    }

    private void SetBusy(bool busy)
    {
        ScanButton.IsEnabled = true;
        ScanButton.Content = busy ? _t["gui_cancel"] : _t["gui_scan"];
        ScanButton.Style = (Style)Application.Current.Resources[busy ? "DefaultButtonStyle" : "AccentButtonStyle"];
        PathBox.IsEnabled = !busy;
        BrowseButton.IsEnabled = !busy;
        Progress.IsIndeterminate = busy;
        if (busy)
        {
            Progress.Value = 0;
        }
    }

    private void UpdateHeaders()
    {
        ThreatsTab.Header = $"{_t["gui_threats"]} ({_threats.Count})";
        ErrorsTab.Header = $"{_t["gui_errors"]} ({_errors.Count})";
    }

    private void ShowStatus(InfoBarSeverity severity, string message)
    {
        StatusBar.Severity = severity;
        StatusBar.Message = message;
    }
}
