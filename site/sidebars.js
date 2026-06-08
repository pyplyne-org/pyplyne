// @ts-check

const sidebars = {
  docs: [
    {
      type: 'doc',
      id: 'README',
      label: 'Overview',
    },
    {
      type: 'category',
      label: 'Start Here',
      link: {
        type: 'generated-index',
        title: 'Start Here',
        description: 'Get oriented, run PyPlyne, and write your first pipelines.',
      },
      collapsed: false,
      items: ['quickstart'],
    },
    {
      type: 'category',
      label: 'Learn The Language',
      link: {
        type: 'generated-index',
        title: 'Learn The Language',
        description: 'Understand PyPlyne concepts, syntax, examples, and workflows.',
      },
      collapsed: false,
      items: ['concepts', 'language-guide', 'sequence-patterns', 'examples', 'cookbook'],
    },
    {
      type: 'category',
      label: 'Work Interactively',
      link: {
        type: 'generated-index',
        title: 'Work Interactively',
        description: 'Use persistent sessions, editor integrations, and CLI commands.',
      },
      collapsed: false,
      items: ['interactive-sessions', 'editor', 'cli', 'generated-cli-reference'],
    },
    {
      type: 'category',
      label: 'Reference',
      link: {
        type: 'generated-index',
        title: 'Reference',
        description: 'Look up language details, Python API usage, and troubleshooting notes.',
      },
      collapsed: true,
      items: ['reference', 'python-api', 'generated-python-api-reference', 'troubleshooting'],
    },
    {
      type: 'category',
      label: 'Project Notes',
      link: {
        type: 'generated-index',
        title: 'Project Notes',
        description: 'Architecture and maintainer notes.',
      },
      collapsed: true,
      items: ['architecture', 'release-versioning'],
    },
  ],
};

module.exports = sidebars;
