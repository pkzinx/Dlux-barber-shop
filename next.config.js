module.exports = {
  // Desativado para evitar warnings do react-slick (findDOMNode em StrictMode)
  reactStrictMode: false,
  eslint: {
    ignoreDuringBuilds: true,
  },
  compiler: {
    // Usa o transform do SWC para styled-components (substitui Babel)
    styledComponents: true,
  },
  output: 'standalone',
};