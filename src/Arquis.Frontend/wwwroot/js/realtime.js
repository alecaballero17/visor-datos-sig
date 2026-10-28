// One shared hub connection per backend, with independent component subscriptions.
window.arquisRealtime = (() => {
    const hubs = new Map();
    const subscriptions = new Map();
    let nextId = 0;
    const events = ['ReceivePosicion', 'ReceivePuntoActualizado', 'ReceiveRutaAsignada',
        'ReceiveRutaActualizada', 'ReceiveOperarioRolActualizado'];
    function notify(hub, method, event) {
        for (const entry of hub.listeners.values()) {
            if (!event || entry.events.includes(event)) {
                entry.reference.invokeMethodAsync(method, ...(method === 'ConnectionChanged' ? [hub.connected] : []))
                    .catch(error => console.debug('Live component unavailable', error));
            }
        }
    }
    function connect(hub) {
        if (hub.listeners.size === 0) return;
        hub.connection.start().then(() => {
            hub.connected = true;
            notify(hub, 'ConnectionChanged');
        }).catch(() => {
            hub.connected = false;
            notify(hub, 'ConnectionChanged');
            hub.retry = setTimeout(() => connect(hub), 5000);
        });
    }
    return {
        subscribe(baseUrl, reference, selectedEvents) {
            let hub = hubs.get(baseUrl);
            if (!hub) {
                const connection = new signalR.HubConnectionBuilder()
                    .withUrl(`${baseUrl.replace(/\/$/, '')}/hubs/tracking`)
                    .withAutomaticReconnect().build();
                hub = { connection, listeners: new Map(), connected: false, retry: null };
                hubs.set(baseUrl, hub);
                for (const event of events) connection.on(event, () => notify(hub, 'Changed', event));
                connection.onreconnecting(() => { hub.connected = false; notify(hub, 'ConnectionChanged'); });
                connection.onreconnected(() => { hub.connected = true; notify(hub, 'ConnectionChanged'); });
                connection.onclose(() => {
                    hub.connected = false;
                    notify(hub, 'ConnectionChanged');
                    if (hub.listeners.size) hub.retry = setTimeout(() => connect(hub), 5000);
                });
            }
            const id = String(++nextId);
            hub.listeners.set(id, { reference, events: selectedEvents });
            subscriptions.set(id, hub);
            if (hub.listeners.size === 1 && hub.connection.state === signalR.HubConnectionState.Disconnected) connect(hub);
            else reference.invokeMethodAsync('ConnectionChanged', hub.connected).catch(() => {});
            return id;
        },
        async unsubscribe(id) {
            const hub = subscriptions.get(id);
            if (!hub) return;
            subscriptions.delete(id);
            hub.listeners.delete(id);
            if (!hub.listeners.size) {
                clearTimeout(hub.retry);
                await hub.connection.stop();
            }
        }
    };
})();
