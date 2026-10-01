using Microsoft.AspNetCore.Components;

namespace Arquis.Frontend.Views.Shared.Labels
{
    public abstract class LabelBaseComponent : ComponentBase
    {
        [Parameter] public string Text { get; set; } = string.Empty;
        [Parameter] public RenderFragment? ChildContent { get; set; }
        [Parameter] public string CssClass { get; set; } = string.Empty;
        [Parameter] public string Icon { get; set; } = string.Empty;
        
        [Parameter(CaptureUnmatchedValues = true)]
        public Dictionary<string, object>? AdditionalAttributes { get; set; }

        protected virtual string DefaultCssClass => "form-label fw-semibold";

        protected string ComputedCssClass => string.IsNullOrWhiteSpace(CssClass)
            ? DefaultCssClass
            : $"{DefaultCssClass} {CssClass}";
    }
}
