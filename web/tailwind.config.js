export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Kanit', 'system-ui', 'sans-serif'],
        mono: ['Cascadia Mono', 'Consolas', 'monospace']
      },
      colors: {
        ground: 'var(--ground)',
        surface: 'var(--surface)',
        side: 'var(--side)',
        fill: 'var(--fill)',
        raised: 'var(--raised)',
        ink: 'var(--ink)',
        soft: 'var(--soft)',
        hint: 'var(--hint)',
        line: 'var(--line)',
        tint: 'var(--tint)',
        'tint-soft': 'var(--tint-soft)',
        ok: 'var(--ok)',
        'ok-soft': 'var(--ok-soft)',
        bad: 'var(--bad)',
        'bad-soft': 'var(--bad-soft)',
        warn: 'var(--warn)',
        'warn-soft': 'var(--warn-soft)'
      },
      boxShadow: {
        float: '0 10px 34px rgba(0, 0, 0, .35)',
        sheet: '0 -10px 50px rgba(0, 0, 0, .22)'
      }
    }
  }
}
