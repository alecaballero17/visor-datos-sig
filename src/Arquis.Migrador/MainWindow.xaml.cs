using Arquis.Migrador.Services;
using Microsoft.Win32;
using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows;

namespace Arquis.Migrador;

public partial class MainWindow : Window
{
    private readonly ShapefileValidator _validator = new();
    private readonly SqlConnectionValidator _connectionValidator = new();
    private string? _selectedFolder;
    private bool _layersAreValid;
    private bool _connectionIsValid;
    private readonly ObservableCollection<LayerInspection> _layers = [];

    public MainWindow()
    {
        InitializeComponent();
        LayersGrid.ItemsSource = _layers;
    }

    private void SelectFolder_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFolderDialog { Title = "Seleccione la carpeta que contiene las cuatro capas SHP" };
        if (dialog.ShowDialog() != true) return;

        _selectedFolder = dialog.FolderName;
        FolderText.Text = _selectedFolder;
        ValidateButton.IsEnabled = true;
        _layers.Clear();
        _layersAreValid = false;
        UpdateImportAvailability();
        DetailsText.Text = "Carpeta seleccionada. Pulse 'Validar capas' para revisar archivos, proyección, geometría y registros.";
    }

    private void Validate_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_selectedFolder)) return;
        _layers.Clear();
        var results = _validator.InspectFolder(_selectedFolder);
        foreach (var result in results) _layers.Add(result);
        _layersAreValid = results.All(x => x.Status.StartsWith("Validación básica correcta", StringComparison.Ordinal));
        UpdateImportAvailability();
        DetailsText.Text = string.Join(Environment.NewLine, results.Select(x => $"{x.DisplayName}: {x.Status}"));
    }

    private async void TestConnection_Click(object sender, RoutedEventArgs e)
    {
        TestConnectionButton.IsEnabled = false;
        try
        {
            var result = await _connectionValidator.TestAsync(ConnectionText.Text);
            _connectionIsValid = result.IsValid;
            DetailsText.Text = result.Message;
            UpdateImportAvailability();
        }
        finally { TestConnectionButton.IsEnabled = true; }
    }

    private void UpdateImportAvailability()
    {
        ImportButton.IsEnabled = _layersAreValid && _connectionIsValid;
        ImportButton.ToolTip = ImportButton.IsEnabled
            ? "Reemplaza las entidades existentes por la carga completa validada."
            : "Primero valide las cuatro capas y pruebe la conexión con SQL Server.";
    }

    private async void Import_Click(object sender, RoutedEventArgs e)
    {
        var projectRoot = FindProjectRoot();
        var script = Path.Combine(projectRoot, "cargar-capas-completas.ps1");
        if (!File.Exists(script))
        {
            DetailsText.Text = "No se encontró el script de carga del proyecto.";
            return;
        }

        if (MessageBox.Show("La importación reemplazará las entidades cartográficas existentes. ¿Desea continuar?", "Confirmar importación", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes)
            return;

        ImportButton.IsEnabled = false;
        DetailsText.Text = "Iniciando carga total...";
        var info = new ProcessStartInfo("powershell.exe", $"-NoProfile -ExecutionPolicy Bypass -File \"{script}\"")
        {
            WorkingDirectory = projectRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        using var process = Process.Start(info);
        if (process is null) { DetailsText.Text = "No se pudo iniciar la importación."; UpdateImportAvailability(); return; }

        while (!process.StandardOutput.EndOfStream)
        {
            var line = await process.StandardOutput.ReadLineAsync();
            if (!string.IsNullOrWhiteSpace(line)) DetailsText.AppendText(Environment.NewLine + line);
        }
        var errors = await process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        DetailsText.AppendText(process.ExitCode == 0 ? Environment.NewLine + "Importación finalizada." : Environment.NewLine + "La importación falló: " + errors);
        UpdateImportAvailability();
    }

    private static string FindProjectRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "Arquis.sln"))) return directory.FullName;
            directory = directory.Parent;
        }
        throw new DirectoryNotFoundException("No se encontró la carpeta raíz del proyecto.");
    }
}
