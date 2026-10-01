using Microsoft.AspNetCore.Components;

namespace Arquis.Frontend.Views.Shared.Buttons
{
    public abstract class ButtonBaseComponent : ComponentBase
    {
        [Parameter] public RenderFragment? ChildContent { get; set; }
        [Parameter] public EventCallback<Microsoft.AspNetCore.Components.Web.MouseEventArgs> OnClick { get; set; }
        [Parameter] public string CssClass { get; set; } = string.Empty;
        [Parameter] public string Type { get; set; } = "button";
        [Parameter] public string Icon { get; set; } = string.Empty;
        
        [Parameter(CaptureUnmatchedValues = true)]
        public Dictionary<string, object>? AdditionalAttributes { get; set; }

        protected virtual string DefaultCssClass => "btn";
        
        protected string ComputedCssClass => string.IsNullOrWhiteSpace(CssClass) 
            ? DefaultCssClass 
            : $"{DefaultCssClass} {CssClass}";
    }
}
