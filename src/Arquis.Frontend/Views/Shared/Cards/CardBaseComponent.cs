using Microsoft.AspNetCore.Components;

namespace Arquis.Frontend.Views.Shared.Cards
{
    public abstract class CardBaseComponent : ComponentBase
    {
        [Parameter] public RenderFragment? ChildContent { get; set; }
        [Parameter] public string CssClass { get; set; } = string.Empty;
        
        [Parameter(CaptureUnmatchedValues = true)]
        public Dictionary<string, object>? AdditionalAttributes { get; set; }

        protected abstract string BaseCssClass { get; }
        protected virtual string DefaultModifiers => string.Empty;

        protected string ComputedCssClass => string.IsNullOrWhiteSpace(CssClass)
            ? $"{BaseCssClass} {DefaultModifiers}".Trim()
            : $"{BaseCssClass} {DefaultModifiers} {CssClass}".Trim();
    }
}
