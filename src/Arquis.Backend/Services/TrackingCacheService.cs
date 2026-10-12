using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Services
{
    public class TrackingCacheService
    {
        private readonly ConcurrentDictionary<string, TrackingPosicion> _posicionesActivas = new();

        public void ActualizarPosicion(TrackingPosicion pos)
        {
            if (string.IsNullOrWhiteSpace(pos.OperarioId)) return;
            pos.Timestamp = DateTime.UtcNow;
            _posicionesActivas[pos.OperarioId] = pos;
        }

        public IEnumerable<TrackingPosicion> ObtenerActivos()
        {
            // Consider active if reported within the last 30 minutes
            var cutoff = DateTime.UtcNow.AddMinutes(-30);
            return _posicionesActivas.Values
                .Where(p => p.Timestamp >= cutoff && p.EnLinea)
                .OrderByDescending(p => p.Timestamp)
                .ToList();
        }

        public TrackingPosicion? ObtenerPorOperario(string operarioId)
        {
            _posicionesActivas.TryGetValue(operarioId, out var pos);
            return pos;
        }

        public void Desconectar(string operarioId)
        {
            if (_posicionesActivas.TryGetValue(operarioId, out var pos))
            {
                pos.EnLinea = false;
            }
        }
    }
}
