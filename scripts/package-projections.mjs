/** Retain the legacy managed protocol until each additional optional package is supported. */
export const managedPackages = (catalog) => catalog.installPackages.filter((pkg) => pkg.managed !== false);
export const providerPackages = (catalog) => catalog.installPackages.filter((pkg) => pkg.providerListed !== false);
export function kiroRoot(name) {
  if (!/^qodo(?:-[a-z0-9-]+)?$/.test(name)) throw new Error('Invalid Qodo package name');
  return name === 'qodo' ? 'kiro-power' : `kiro-power-${name.slice('qodo-'.length)}`;
}
