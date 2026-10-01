using Microsoft.AspNetCore.Components;

namespace Arquis.Frontend.Views.Shared.Badges
{
    public abstract class BadgeBaseComponent : ComponentBase
    {
        [Parameter] public RenderFragment? ChildContent { get; set; }
        [Parameter] public string CssClass { get; set; } = string.Empty;
        
        [Parameter(CaptureUnmatchedValues = true)]
        public Dictionary<string, object>? AdditionalAttributes { get; set; }

        protected virtual string DefaultCssClass => "badge";

        protected string ComputedCssClass => string.IsNullOrWhiteSpace(CssClass)
            ? DefaultCssClass
            : $"{DefaultCssClass} {CssClass}";
    }
}
