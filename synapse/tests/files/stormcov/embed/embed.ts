// Storm embedded in TypeScript for the stormcov tests. embed.json lists it.
const storm = (strings: TemplateStringsArray) => strings[0];

export async function addFqdn(optic, fqdn) {
    return optic.callStorm(storm`
        [ inet:fqdn=$fqdn ]
        if (true) {
            [ inet:fqdn=ts.link ]
        }
    `, { vars: { fqdn } });
}

export const QUERY = storm`inet:fqdn=ts.link | limit 1`;
