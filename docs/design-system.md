# Track it design system

Track it is a local AI rotoscoping, mask-correction, and motion-tracking workbench for
consumer and prosumer creators. Its single job is to select a visible subject, verify or
correct its mask through time, and export masks or motion data.

## Digital Rotoscope Bench

The canvas is a quiet, calibrated tracing surface. Tool rail, inspector, transport,
timeline, and status strip act as instruments around it—not floating SaaS cards. The sole
signature is a functional dual-frame edge echo: cobalt for the accepted edge, coral for the
previous visible edge, and teal for the next visible edge. It is optional, confined to the
canvas, and static when reduced motion is enabled.

Dark palette: canvas `#090B10`, workspace `#11151B`, surface `#191E27`, text `#F2F5F8`,
trace `#6D87FF`, previous `#FF8278`, next `#43CEBA`, muted `#98A3B3`, border `#303846`.

Light palette: canvas `#DDE3EC`, workspace `#EEF2F7`, surface `#FFFFFF`, text `#171B23`,
trace `#3658D6`, previous `#C94E48`, next `#087F73`, muted `#5E6979`, border `#C8D0DC`.

Widgets consume semantic tokens from `ThemeManager`; widget code contains no palette hex.
Spacing is 4, 8, 12, 16, 24, 32, and 48 pixels. Radii are 4 pixels for controls, 6 for
menus and dialogs, and 8 for major overlays. Dividers precede shadows.

Host Grotesk is the display, body, and control family. Its uniwidth construction keeps labels
and transport controls stable as values change while its open forms remain clear at compact
desktop sizes. JetBrains Mono/system monospace remains the data role for timecode, frames, and
memory values. Type sizes are 12, 13, 14, 16, 18, 22, and 30 pixels.

```text
project header                                      theme · model · Export
tool rail |                 video canvas                 | object inspector
          | transport · tracking · frame/timecode        |
timeline: objects · masks · cuts · corrections · confidence · range
backend · model · device · operation · Local only
```

Default size is 1440×900 and minimum is 1100×700. Critical actions pair Material Symbols
with visible text. Keyboard focus is visible, status never relies on color alone, normal
text targets 4.5:1 contrast, and glyphs target 3:1.
