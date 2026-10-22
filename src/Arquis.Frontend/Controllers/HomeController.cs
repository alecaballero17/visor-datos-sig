using Microsoft.AspNetCore.Mvc;
using System.Net.Http.Json;

namespace Arquis.Frontend.Controllers;
public sealed class HomeController(IConfiguration config, IHttpClientFactory httpClients) : Controller
{
    public IActionResult Login() { ViewBag.BackendBaseUrl=config["BackendBaseUrl"] ?? "http://localhost:5080"; return View(); }

    public async Task<IActionResult> Index(CancellationToken ct)
    {
        ViewBag.BackendBaseUrl=config["BackendBaseUrl"] ?? "http://localhost:5080";
        var cookie=Request.Headers.Cookie.ToString();
        if (string.IsNullOrWhiteSpace(cookie)) return RedirectToAction(nameof(Login));

        try
        {
            using var request=new HttpRequestMessage(HttpMethod.Get,$"{ViewBag.BackendBaseUrl}/api/autenticacion/sesion");
            request.Headers.TryAddWithoutValidation("Cookie",cookie);
            using var response=await httpClients.CreateClient().SendAsync(request,ct);
            if (!response.IsSuccessStatusCode) return RedirectToAction(nameof(Login));
            var session=await response.Content.ReadFromJsonAsync<SessionResponse>(cancellationToken:ct);
            if (session?.Roles?.Contains("Administrador",StringComparer.Ordinal)==true) return View();
        }
        catch (HttpRequestException) { }
        catch (TaskCanceledException) when (!ct.IsCancellationRequested) { }

        ViewBag.LoginMessage="La versión web está habilitada únicamente para el usuario administrador.";
        return View("Login");
    }

    private sealed record SessionResponse(string[]? Roles);
}
