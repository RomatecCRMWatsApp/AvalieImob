// @module utils/latLonToUTM — Conversão lat/lon → UTM (SIRGAS 2000 ≈ WGS84).
// SIRGAS 2000 e WGS84 são praticamente coincidentes para fins de UTM (erro < 1m),
// então usamos os parâmetros do elipsoide GRS80/WGS84 (a=6378137, f=1/298.257222101).

const A = 6378137.0;            // semieixo maior (GRS80/SIRGAS2000)
const F = 1 / 298.257222101;   // achatamento
const K0 = 0.9996;
const E2 = F * (2 - F);
const EP2 = E2 / (1 - E2);

/**
 * Converte latitude/longitude (graus decimais) para UTM.
 * Retorna { zona, hemisferio, easting, northing, label }.
 */
export function latLonToUTM(lat, lon) {
  const rad = Math.PI / 180;
  const zona = Math.floor((lon + 180) / 6) + 1;
  const lonOrigem = (zona - 1) * 6 - 180 + 3; // meridiano central da zona
  const latR = lat * rad;
  const lonR = lon * rad;
  const lonOR = lonOrigem * rad;

  const N = A / Math.sqrt(1 - E2 * Math.sin(latR) ** 2);
  const T = Math.tan(latR) ** 2;
  const C = EP2 * Math.cos(latR) ** 2;
  const Aa = Math.cos(latR) * (lonR - lonOR);

  const M = A * (
    (1 - E2 / 4 - (3 * E2 * E2) / 64 - (5 * E2 ** 3) / 256) * latR
    - ((3 * E2) / 8 + (3 * E2 * E2) / 32 + (45 * E2 ** 3) / 1024) * Math.sin(2 * latR)
    + ((15 * E2 * E2) / 256 + (45 * E2 ** 3) / 1024) * Math.sin(4 * latR)
    - ((35 * E2 ** 3) / 3072) * Math.sin(6 * latR)
  );

  let easting = K0 * N * (
    Aa + ((1 - T + C) * Aa ** 3) / 6
    + ((5 - 18 * T + T * T + 72 * C - 58 * EP2) * Aa ** 5) / 120
  ) + 500000.0;

  let northing = K0 * (M + N * Math.tan(latR) * (
    (Aa * Aa) / 2 + ((5 - T + 9 * C + 4 * C * C) * Aa ** 4) / 24
    + ((61 - 58 * T + T * T + 600 * C - 330 * EP2) * Aa ** 6) / 720
  ));

  const hemisferio = lat < 0 ? 'S' : 'N';
  if (lat < 0) northing += 10000000.0; // falso norte no hemisfério sul

  return {
    zona,
    hemisferio,
    easting,
    northing,
    label: `UTM ${zona}${hemisferio} · E=${Math.round(easting).toLocaleString('pt-BR')} · N=${Math.round(northing).toLocaleString('pt-BR')} (SIRGAS 2000)`,
  };
}
