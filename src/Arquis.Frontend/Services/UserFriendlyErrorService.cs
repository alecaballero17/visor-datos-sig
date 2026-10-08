using System.Net;

namespace Arquis.Frontend.Services;

public enum ErrorSeverity
{
    Info,
    Warning,
    Danger
}

public sealed class UserErrorMessage
{
    public string Id { get; } = Guid.NewGuid().ToString("N");
    public string Title { get; set; } = "Aviso del Sistema";
    public string Message { get; set; } = "Ha ocurrido una situación inesperada.";
    public string? Recommendation { get; set; }
    public string Icon { get; set; } = "bi-info-circle";
    public ErrorSeverity Severity { get; set; } = ErrorSeverity.Warning;
    public string? TechnicalDetail { get; set; }
    public string? ActionText { get; set; }
    public Func<Task>? OnAction { get; set; }
    public DateTime Timestamp { get; } = DateTime.Now;

    public string BadgeCssClass => Severity switch
    {
        ErrorSeverity.Danger => "bg-danger-subtle text-danger border-danger-subtle",
        ErrorSeverity.Warning => "bg-warning-subtle text-warning-emphasis border-warning-subtle",
        _ => "bg-info-subtle text-info border-info-subtle"
    };

    public string AlertCssClass => Severity switch
    {
        ErrorSeverity.Danger => "alert-danger border-danger-subtle",
        ErrorSeverity.Warning => "alert-warning border-warning-subtle",
        _ => "alert-info border-info-subtle"
    };
}

public interface IUserFriendlyErrorService
{
    event Action<UserErrorMessage>? OnNotification;
    event Action<string>? OnDismiss;

    void Notify(UserErrorMessage message);
    void Dismiss(string messageId);

    UserErrorMessage FromStatusCode(HttpStatusCode statusCode, string? context = null, string? technicalDetail = null, Func<Task>? retryAction = null);
    UserErrorMessage FromException(Exception ex, string? context = null, Func<Task>? retryAction = null);
}

public sealed class UserFriendlyErrorService : IUserFriendlyErrorService
{
    public event Action<UserErrorMessage>? OnNotification;
    public event Action<string>? OnDismiss;

    public void Notify(UserErrorMessage message)
    {
        OnNotification?.Invoke(message);
    }

    public void Dismiss(string messageId)
    {
        OnDismiss?.Invoke(messageId);
    }

    public UserErrorMessage FromStatusCode(HttpStatusCode statusCode, string? context = null, string? technicalDetail = null, Func<Task>? retryAction = null)
    {
        var msg = new UserErrorMessage
        {
            TechnicalDetail = technicalDetail ?? $"Código HTTP: {(int)statusCode} ({statusCode})",
            OnAction = retryAction,
            ActionText = retryAction != null ? "Reintentar" : null
        };

        switch (statusCode)
        {
            case HttpStatusCode.Unauthorized:
            case HttpStatusCode.Forbidden:
                msg.Title = "Sesión Finalizada";
                msg.Message = "Tu sesión de usuario ha expirado o no dispones de los permisos para esta consulta.";
                msg.Recommendation = "Por favor, inicia sesión nuevamente para continuar navegando el mapa.";
                msg.Icon = "bi-shield-lock-fill";
                msg.Severity = ErrorSeverity.Warning;
                msg.ActionText = "Ir a Iniciar Sesión";
                break;

            case HttpStatusCode.NotFound:
                msg.Title = context != null ? $"No se encontró {context}" : "Elemento no encontrado";
                msg.Message = "El predio, código o capa cartográfica solicitada no existe o fue reubicada en el catastro.";
                msg.Recommendation = "Verifica que el número de lote, código o manzana sean correctos e intenta otra búsqueda.";
                msg.Icon = "bi-search";
                msg.Severity = ErrorSeverity.Info;
                break;

            case HttpStatusCode.RequestTimeout:
            case HttpStatusCode.GatewayTimeout:
                msg.Title = "La consulta tardó más de lo esperado";
                msg.Message = "El servidor de mapas está tardando en procesar los datos espaciales debido al volumen de polígonos.";
                msg.Recommendation = "Acércate más con el zoom en el mapa para cargar menos elementos a la vez.";
                msg.Icon = "bi-hourglass-split";
                msg.Severity = ErrorSeverity.Warning;
                break;

            case HttpStatusCode.ServiceUnavailable:
            case HttpStatusCode.BadGateway:
            case HttpStatusCode.InternalServerError:
                msg.Title = "Servicio Cartográfico Ocupado";
                msg.Message = "Estamos experimentando una interrupción temporal en el servidor de datos espaciales.";
                msg.Recommendation = "No te preocupes, tus datos no se perdieron. Espera unos instantes y pulsa Reintentar.";
                msg.Icon = "bi-cloud-slash-fill";
                msg.Severity = ErrorSeverity.Danger;
                break;

            default:
                msg.Title = "No se pudo completar la operación";
                msg.Message = "Ocurrió una situación inesperada al consultar la información geográfica.";
                msg.Recommendation = "Si el problema persiste, refresca la página o contacta con el administrador del sistema.";
                msg.Icon = "bi-exclamation-octagon-fill";
                msg.Severity = ErrorSeverity.Warning;
                break;
        }

        Notify(msg);
        return msg;
    }

    public UserErrorMessage FromException(Exception ex, string? context = null, Func<Task>? retryAction = null)
    {
        var msg = new UserErrorMessage
        {
            TechnicalDetail = $"{ex.GetType().Name}: {ex.Message}",
            OnAction = retryAction,
            ActionText = retryAction != null ? "Reintentar" : null
        };

        if (ex is HttpRequestException httpEx)
        {
            if (httpEx.StatusCode.HasValue)
            {
                return FromStatusCode(httpEx.StatusCode.Value, context, ex.ToString(), retryAction);
            }

            msg.Title = "Sin conexión con el servidor";
            msg.Message = "No pudimos conectar con el servidor local del visor de mapas.";
            msg.Recommendation = "Asegúrate de tener conexión a la red y de que los servicios locales de backend se encuentren activos.";
            msg.Icon = "bi-wifi-off";
            msg.Severity = ErrorSeverity.Danger;
        }
        else if (ex is TaskCanceledException or OperationCanceledException)
        {
            msg.Title = "Consulta cancelada";
            msg.Message = "La búsqueda fue reemplazada por una consulta más reciente.";
            msg.Recommendation = "Escribe tu criterio y espera un instante a que aparezcan los resultados.";
            msg.Icon = "bi-arrow-repeat";
            msg.Severity = ErrorSeverity.Info;
        }
        else
        {
            msg.Title = "Consulta de mapa interrumpida";
            msg.Message = "No se pudieron obtener todos los detalles del predio en este momento.";
            msg.Recommendation = "Intenta mover el mapa o seleccionar el predio nuevamente.";
            msg.Icon = "bi-exclamation-triangle-fill";
            msg.Severity = ErrorSeverity.Warning;
        }

        Notify(msg);
        return msg;
    }
}
