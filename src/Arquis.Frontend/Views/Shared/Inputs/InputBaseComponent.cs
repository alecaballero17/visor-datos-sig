using Microsoft.AspNetCore.Components;

namespace Arquis.Frontend.Views.Shared.Inputs
{
    public abstract class InputBaseComponent<TValue> : ComponentBase
    {
        [Parameter] public string Id { get; set; } = Guid.NewGuid().ToString();
        [Parameter] public string Label { get; set; } = string.Empty;
        [Parameter] public TValue? Value { get; set; }
        [Parameter] public EventCallback<TValue?> ValueChanged { get; set; }
        [Parameter] public string CssClass { get; set; } = "form-control";
        [Parameter] public bool Required { get; set; } = false;

        protected async Task OnValueChanged(ChangeEventArgs e)
        {
            if (e.Value == null)
            {
                Value = default;
            }
            else if (typeof(TValue) == typeof(string))
            {
                Value = (TValue)(object)e.Value.ToString()!;
            }
            else
            {
                // Basic conversion for other types if needed, 
                // but usually handled specifically by derived classes
                try {
                    Value = (TValue)Convert.ChangeType(e.Value, typeof(TValue));
                } catch {
                    Value = default;
                }
            }
            
            await ValueChanged.InvokeAsync(Value);
        }
    }
}
