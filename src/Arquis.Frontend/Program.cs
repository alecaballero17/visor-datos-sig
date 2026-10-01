var builder = WebApplication.CreateBuilder(args);
builder.Services.AddRazorComponents().AddInteractiveServerComponents();
builder.Services.AddScoped(sp => {
    var handler = new HttpClientHandler { 
        CookieContainer = new System.Net.CookieContainer(),
        UseCookies = true 
    };
    return new HttpClient(handler) { BaseAddress = new Uri("http://localhost:5080/") };
});
var app = builder.Build();
if (!app.Environment.IsDevelopment()) app.UseExceptionHandler("/Error", createScopeForErrors: true);
app.UseStaticFiles();
app.UseAntiforgery();
app.MapRazorComponents<Arquis.Frontend.App>().AddInteractiveServerRenderMode();
app.Run();
