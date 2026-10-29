# jic-sf-ui-style: project reference for {{project}}

<!--
Lives at <repo>/.claude/skills/jic-sf-ui-style/references/project.md. It holds the project's bindings of the JIC
Smart Factory style; it overrides the generic skill where they differ. No SKILL.md in that folder: a personal skill
wins over a project skill of the same name, so a project copy would be ignored. Brand-independent UI rules are
project-style-rpx references/ui.md; this file does not restate them. Record what is, with the test that holds it.
-->

## Modules

| Need | Module |
|---|---|
| A colour token | `{{theme module}}` (Qt-free), re-exported by `{{style module}}` |
| Font, density, `Token_Color`, hairline, scroll style | `{{style module}}` |
| Widgets | `{{widgets module}}` |
| Header and window layout | `{{window module}}` |
| Pixel icons, motif | `{{module}}` |
| Grid-fitting | `{{module}}` |
| Charts | `{{module}}` |
| Image marks | `{{module}}` |
| Operator wording | `{{module}}` |

## Views and their states

{{The project's views, its state colours (token, value, contrast), and what each view draws.}}

## Overlays and image marks

{{What the project draws on images, with its measurements.}}

## Wording

{{The project's state lines, kinds and names.}}

## Logos, band and density

{{The product logo, its lockup constants, the band's logos and disclaimer constant, the density check.}}

## Tests

| Rule | Test |
|---|---|
| {{rule}} | `{{test}}` |

## Departures and Unsettled

{{Each departure from the generic style with its reason; practices not yet settled.}}
