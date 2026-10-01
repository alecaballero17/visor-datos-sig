using Microsoft.AspNetCore.Components;

namespace Arquis.Frontend.Views.Shared.Checkboxes
{
    public abstract class CheckboxBaseComponent : ComponentBase
    {
        [Parameter] public string Id { get; set; } = Guid.NewGuid().ToString();
        [Parameter] public string Label { get; set; } = string.Empty;
        [Parameter] public bool Value { get; set; }
        [Parameter] public EventCallback<bool> ValueChanged { get; set; }
        [Parameter] public string CssClass { get; set; } = "form-check";

        protected async Task OnValueChanged(ChangeEventArgs e)
        {
            if (e.Value is bool boolValue)
            {
                Value = boolValue;
                await ValueChanged.InvokeAsync(Value);
            }
        }
    }
}
