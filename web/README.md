# BlockHistory website

Next.js 16 (App Router) and MapLibre 6. See the [project README](../README.md).

```
npm install
npm run dev        # also copies the MapLibre worker into public/; use this, not `npx next dev`
npm run typecheck
npm run build
```

- Data: `lib/data.ts` reads Supabase when `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set in
  `.env.local`, otherwise `../data/blockhistory.sqlite`.
- `lib/area.json` (area and map years) and `public/overlays/` are written by
  `scripts/export_overlays.py`; `lib/accuracy.json` by `scripts/check_accuracy.py --update`.
- `/status` checks the address service, database and Library of Congress images when opened,
  and shows the last weekly check (`.github/workflows/weekly.yml`).
