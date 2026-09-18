using Microsoft.AspNetCore.Mvc;
namespace Arquis.Frontend.Controllers;
public sealed class HomeController(IConfiguration config) : Controller
{
    public IActionResult Login() { ViewBag.BackendBaseUrl=config["BackendBaseUrl"] ?? "http://localhost:5080"; return View(); }
    public IActionResult Index() { ViewBag.BackendBaseUrl=config["BackendBaseUrl"] ?? "http://localhost:5080"; return View(); }
}
