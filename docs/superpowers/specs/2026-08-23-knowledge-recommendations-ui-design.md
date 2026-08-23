# Knowledge Recommendations UI Design

## Objective

Make the Data Transformation workspace faster to scan and reuse. The page will lead with the natural-language requirement, show mocked knowledge-base recommendations immediately below it, and let a user inspect a recommendation before applying only its source datasets to the current request.

This iteration is a frontend POC. It does not add a knowledge-base backend, change Spark SQL generation, or submit a Spark job.

## User Flow

The transformation flow is presented in this order:

1. Transformation Requirement
2. Source Data
3. Generated Spark SQL
4. Sink Dataset

The user enters or edits the request name and natural-language transformation requirement in step 1. When the requirement contains text, a compact “Similar Knowledge & Jobs” area shows three or four relevant mocked recommendations. Recommendations may represent an online scheduled job or a historical request.

Clicking a recommendation opens a read-only detail modal containing:

- recommendation type, title, similarity, and status;
- original requirement;
- source datasets and their primary/auxiliary roles;
- Spark SQL;
- sink dataset;
- schedule and last-run information when available.

The modal has a `Use Sources` action. Selecting it replaces the current source selection and primary source with the recommendation’s source snapshot. It intentionally does not replace the current request name, natural-language requirement, or sink configuration. Any previously generated Spark SQL is cleared because it may no longer be valid for the new source set. The modal then closes.

## Information Architecture

The progress strip and section numbering use the new order. Step 1 contains the request fields followed by the recommendations. Step 2 retains the compact selected-source list, the `+ Add` modal, primary-source controls, removal controls, and dataset-detail modal. Steps 3 and 4 retain the existing Spark SQL and sink behavior.

The recommendation area has two visually distinct categories without adding navigation complexity:

- `Online Job`: an existing scheduled transformation, displaying schedule and operational state.
- `History`: a prior transformation request, displaying last-used time and final state.

Recommendation cards show only the information needed for comparison: type, title, similarity percentage, source count, and schedule or last-used time. Full snapshots stay in the modal.

## Recommendation Model and Matching

Mock recommendation data lives in a dedicated frontend module rather than inside the page component. Each item contains a stable ID, kind, title, requirement, searchable keywords, similarity baseline, source snapshot, Spark SQL snapshot, sink snapshot, status, and optional schedule/last-run fields.

A small pure matching function accepts the current natural-language requirement and the mock catalog. It normalizes case and whitespace, scores keyword overlap, combines it with the item’s baseline score, sorts descending, and returns at most four results. An empty requirement returns no results. If no keyword overlaps, the highest-baseline examples may still be shown as low-confidence suggestions so the POC never appears broken after meaningful input.

Source application is also a pure operation: it derives selected table names and the primary table from the recommendation snapshot. Only datasets present in the current metadata catalog are applied. If the recommended primary dataset is unavailable, the first available recommended source becomes primary. If no recommended sources exist in the current catalog, the UI leaves the current sources unchanged and displays an inline error in the modal.

## Visual Direction

The application moves from dark green and lime toward a brighter data-workbench palette:

- cold white and pale blue-gray surfaces;
- electric blue for primary actions, selected navigation, focus rings, and progress states;
- teal for validation and successful states;
- restrained violet and cyan accents for recommendation types and data tiers;
- neutral slate text with high contrast.

The sidebar remains dark enough to anchor the workspace, but uses a blue-slate background instead of green. Navigation labels use smaller type, weight 400 or 500, reduced row height, and quieter icons. The active item uses a translucent blue highlight and a slim blue accent.

The transformation workspace becomes approximately 15–20 percent denser through smaller section padding, shorter fields, tighter card gaps, a shorter progress strip, and more restrained heading sizes. Density must not reduce click targets below a practical size or remove existing labels.

## Component Boundaries

- `knowledgeRecommendations.ts` owns recommendation types, fixtures, matching, and source-resolution helpers. It has no React dependency.
- `KnowledgeRecommendations` renders the recommendation summary cards and empty state.
- `KnowledgeRecommendationModal` renders the complete read-only snapshot and calls `onUseSources`.
- `TransformationBuilder` owns current form state, calls the matcher, opens the modal, and applies the resolved sources.
- Existing dataset picker and dataset detail components remain the source of truth for metadata browsing.

These boundaries keep the eventual provider migration small: the mock array and matcher can later be replaced by a KB API response without changing how the builder applies a recommendation.

## State Transitions

Applying a recommendation produces these state changes atomically:

- `selected` becomes the resolved recommended source table list;
- `primary` becomes the resolved recommended primary table;
- `sql` becomes `null`;
- `requirement`, `name`, and `sink` remain unchanged;
- the recommendation modal closes;
- any prior source-application error is cleared.

Editing the requirement recomputes recommendations locally. It does not automatically change any source, SQL, or sink state.

## Error and Empty States

- Empty requirement: show a quiet prompt to describe the transformation before recommendations appear.
- No strong match: show low-confidence mock suggestions with their displayed similarity; do not claim an exact match.
- Missing recommended datasets: disable source application only when none of the snapshot datasets exist in current metadata and explain why in the modal.
- Partial availability: apply available datasets, choose a valid primary, and state in the modal that unavailable sources will be skipped before the user confirms.

No backend error path is introduced because recommendation lookup is local in this POC.

## Accessibility and Interaction

Recommendation cards are buttons with visible keyboard focus. The detail modal uses dialog semantics, has a descriptive accessible label, closes through its close button or backdrop, and does not treat snapshot rows as interactive controls. Existing source rows remain keyboard-openable for dataset details.

All visible product copy remains English.

## Testing and Verification

Automated tests cover the pure recommendation behavior:

- empty requirements return no recommendations;
- relevant keywords rank matching online jobs/history first;
- results are limited to four and sorted by score;
- applying a recommendation resolves source names and the primary role;
- unavailable sources are skipped and the primary fallback is deterministic.

UI-level assertions cover:

- step order is Requirement, Source Data, Spark SQL, Sink Dataset;
- recommendation detail exposes source, Spark SQL, and sink snapshots;
- `Use Sources` changes sources and clears generated SQL while preserving the current requirement and sink.

Final verification includes the frontend test suite, TypeScript/Vite production build, backend regression tests, and a browser smoke test of the complete recommendation-to-source flow at desktop and narrow viewport widths.

## Out of Scope

- A real knowledge-base provider or backend endpoint.
- Persisting recommendation selection.
- Copying recommendation SQL, sink, request name, or requirement into the current request.
- Executing or scheduling Spark jobs.
- Changing the existing Anthropic Spark SQL generation and SQLGlot validation contract.
