using Arquis.Migrador.Services;
using Microsoft.Win32;
using System;
using System.Collections.ObjectModel;
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
            ? "La importación estará disponible en el siguiente bloque de desarrollo."
            : "Primero valide las cuatro capas y pruebe la conexión con SQL Server.";
    }
}
