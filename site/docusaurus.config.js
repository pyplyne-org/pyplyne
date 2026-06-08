// @ts-check

const {themes} = require('prism-react-renderer');

const config = {
  title: 'PyPlyne',
  tagline: 'Clean functional pipes for Python data transformations.',
  favicon: 'img/favicon.svg',
  url: 'https://pyplyne.org',
  baseUrl: '/',
  organizationName: 'pyplyne-org',
  projectName: 'pyplyne',
  onBrokenLinks: 'throw',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'throw',
    },
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: '../docs',
          routeBasePath: 'docs',
          sidebarPath: require.resolve('./sidebars.js'),
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],

  plugins: [require.resolve('docusaurus-lunr-search')],

  themeConfig: {
    navbar: {
      title: 'PyPlyne',
      logo: {
        alt: 'PyPlyne logo',
        src: 'img/pyplyne-icon.svg',
      },
      items: [
        {to: '/docs/', label: 'Docs', position: 'left'},
        {to: '/docs/quickstart', label: 'Quickstart', position: 'left'},
        {to: '/docs/reference', label: 'Reference', position: 'left'},
        {to: '/docs/interactive-sessions', label: 'Sessions', position: 'left'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Quickstart', to: '/docs/quickstart'},
            {label: 'Language Guide', to: '/docs/language-guide'},
            {label: 'Language Reference', to: '/docs/reference'},
            {label: 'CLI Reference', to: '/docs/cli'},
          ],
        },
        {
          title: 'Project',
          items: [
            {label: 'Interactive Sessions', to: '/docs/interactive-sessions'},
            {label: 'Architecture', to: '/docs/architecture'},
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} PyPlyne contributors.`,
    },
    prism: {
      theme: themes.github,
      darkTheme: themes.oneDark,
      additionalLanguages: ['python', 'bash'],
    },
  },
};

module.exports = config;
