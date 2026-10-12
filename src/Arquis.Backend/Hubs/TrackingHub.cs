using System.Threading.Tasks;
using Microsoft.AspNetCore.SignalR;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Hubs
{
    public class TrackingHub : Hub
    {
        public async Task EnviarPosicion(TrackingPosicion pos)
        {
            await Clients.Others.SendAsync("ReceivePosicion", pos);
        }

        public async Task NotificarRutaAsignada(RutaTrabajo ruta)
        {
            await Clients.All.SendAsync("ReceiveRutaAsignada", ruta);
        }

        public async Task NotificarPuntoCompletado(int rutaId, int puntoId, string estado)
        {
            await Clients.All.SendAsync("ReceivePuntoActualizado", new { rutaId, puntoId, estado });
        }
    }
}
