using Microsoft.AspNetCore.Components;
using Microsoft.JSInterop;
using System.Text.Json;

namespace Arquis.Frontend.Views.Shared.Maps
{
    public abstract class MapBaseComponent : ComponentBase, IAsyncDisposable
    {
        [Inject] protected IJSRuntime JS { get; set; } = default!;
        [Inject] protected HttpClient Http { get; set; } = default!;

        [Parameter] public string Height { get; set; } = "400px";
        [Parameter] public string Width { get; set; } = "100%";
        [Parameter] public double CenterLat { get; set; } = -16.39;
        [Parameter] public double CenterLng { get; set; } = -60.965;
        [Parameter] public int Zoom { get; set; } = 14;
        
        [Parameter] public EventCallback<string> OnBboxChanged { get; set; }
        [Parameter] public EventCallback<(string LayerId, string FeatureJson)> OnFeatureSelected { get; set; }

        protected string mapElementId = "map-" + Guid.NewGuid().ToString("N");
        protected bool isLoaded = false;
        private DotNetObjectReference<MapBaseComponent>? dotNetRef;
        
        [Parameter(CaptureUnmatchedValues = true)]
        public Dictionary<string, object>? AdditionalAttributes { get; set; }

        protected virtual string MapContainerStyle => $"height: {Height}; width: {Width}; border-radius: 8px; border: 1px solid #ddd; z-index: 1;";

        protected override async Task OnAfterRenderAsync(bool firstRender)
        {
            if (firstRender)
            {
                dotNetRef = DotNetObjectReference.Create(this);
                await JS.InvokeVoidAsync("mapInterop.initializeMap", mapElementId, dotNetRef, CenterLat, CenterLng, Zoom);
                isLoaded = true;
                StateHasChanged();
            }
        }

        [JSInvokable]
        public async Task OnMapMoveEnd(string bbox)
        {
            await OnBboxChanged.InvokeAsync(bbox);
        }

        [JSInvokable]
        public async Task OnFeatureClicked(string layerId, string featureJson)
        {
            await OnFeatureSelected.InvokeAsync((layerId, featureJson));
        }

        public async Task UpdateLayerAsync(string layerId, string bbox, string color = "#38bdf8", int weight = 2, double fillOpacity = 0.12)
        {
            if (!isLoaded) return;
            
            try
            {
                var response = await Http.GetAsync($"api/capas/{layerId}/geojson?bbox={Uri.EscapeDataString(bbox)}&limit=1800");
                if (response.IsSuccessStatusCode)
                {
                    var geoJsonStr = await response.Content.ReadAsStringAsync();
                    using var doc = JsonDocument.Parse(geoJsonStr);
                    // Pasamos el JsonDocument a JSInterop
                    await JS.InvokeVoidAsync("mapInterop.updateLayer", layerId, doc.RootElement, color, weight, fillOpacity);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error actualizando capa {layerId}: {ex.Message}");
            }
        }

        public async Task RemoveLayerAsync(string layerId)
        {
            if (!isLoaded) return;
            await JS.InvokeVoidAsync("mapInterop.removeLayer", layerId);
        }

        public async ValueTask DisposeAsync()
        {
            dotNetRef?.Dispose();
        }
    }
}
