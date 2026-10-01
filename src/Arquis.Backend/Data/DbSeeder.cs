using System.Threading.Tasks;
using Arquis.Backend.Data.Seeders;

namespace Arquis.Backend.Data
{
    public static class DbSeeder
    {
        public static async Task SeedAsync(ArquisDbContext context)
        {
            await RoleSeeder.SeedAsync(context);
            await UserSeeder.SeedAsync(context);
            await MenuSeeder.SeedAsync(context);
            await GeoDataSeeder.SeedAsync(context);
        }
    }
}
