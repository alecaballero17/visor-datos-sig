using Microsoft.JSInterop;

namespace Arquis.Frontend;

/// <summary>
/// Llamadas a las funciones del mapa (window.arquis.*). En Blazor Server una excepcion de
/// JavaScript no capturada cierra el circuito: la pagina deja de responder y el mapa
/// "desaparece". Un fallo al dibujar o mover el mapa no debe tumbar toda la sesion.
/// </summary>
public static class MapaInterop
{
    public static async ValueTask MapaAsync(this IJSRuntime js, string funcion, params object?[] args)
    {
        try
        {
            await js.InvokeVoidAsync(funcion, args);
        }
        catch (JSException ex)
        {
            Console.Error.WriteLine($"[mapa] {funcion} fallo en el navegador: {ex.Message.Split('\n')[0]}");
        }
        catch (JSDisconnectedException)
        {
            // El usuario cerro o recargo la pagina: no hay a quien avisar.
        }
        catch (TaskCanceledException)
        {
            // Circuito cerrandose.
        }
    }
}
