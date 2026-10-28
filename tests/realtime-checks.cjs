const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function main() {
    const hubs = [], calls = [];
    class Hub {
        constructor() { this.state = 'Disconnected'; this.events = new Map(); hubs.push(this); }
        on(event, handler) { this.events.set(event, handler); }
        onreconnecting(handler) { this.reconnecting = handler; }
        onreconnected(handler) { this.reconnected = handler; }
        onclose(handler) { this.closed = handler; }
        async start() { this.state = 'Connected'; }
        async stop() { this.state = 'Disconnected'; this.closed(); }
    }
    class Builder {
        withUrl(url) { this.url = url; return this; }
        withAutomaticReconnect() { return this; }
        build() { return new Hub(); }
    }
    const window = {};
    vm.runInNewContext(fs.readFileSync('src/Arquis.Frontend/wwwroot/js/realtime.js', 'utf8'), {
        window, signalR: { HubConnectionBuilder: Builder, HubConnectionState: { Disconnected: 'Disconnected' } },
        setTimeout, clearTimeout, console
    });
    const reference = id => ({ invokeMethodAsync: async (...args) => calls.push([id, ...args]) });
    const api = window.arquisRealtime;
    const a = api.subscribe('http://localhost:5080', reference('a'), ['ReceivePosicion']);
    const b = api.subscribe('http://localhost:5080', reference('b'), ['ReceivePuntoActualizado']);
    await Promise.resolve();
    assert.equal(hubs.length, 1, 'Subscribers share a single connection');
    calls.length = 0;
    hubs[0].events.get('ReceivePosicion')();
    assert.deepEqual(calls, [['a', 'Changed']], 'Position events reach only interested components');
    calls.length = 0;
    hubs[0].events.get('ReceivePuntoActualizado')();
    assert.deepEqual(calls, [['b', 'Changed']], 'Completion events reach dashboard subscribers');
    calls.length = 0;
    hubs[0].reconnecting();
    assert(calls.every(call => call[1] === 'ConnectionChanged' && call[2] === false));
    calls.length = 0;
    hubs[0].reconnected();
    assert.equal(calls.length, 2);
    assert(calls.every(call => call[2] === true), 'Reconnection requests a fresh snapshot');
    await api.unsubscribe(a);
    calls.length = 0;
    hubs[0].events.get('ReceivePosicion')();
    assert.equal(calls.length, 0, 'Disposed components receive no updates');
    await api.unsubscribe(b);
    assert.equal(hubs[0].state, 'Disconnected', 'Last subscriber closes the hub');
    console.log('PASS: shared connection, event filtering, disconnect/reconnect and subscription cleanup');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
