# Risk Assessment Skill

## Triggers
- "assess risks", "risk analysis", "risk register", "/risk-assess"

## Workflow
1. Analyze the current note or conversation context for potential risks
2. Use `search_issues` to find related issues with risk indicators
3. Generate a Risk Register PM block with:
   - Identified risks with descriptions
   - Probability (1-5) and Impact (1-5) scores
   - Risk score = P × I
   - Mitigation strategy (avoid, mitigate, transfer, accept)
   - Risk owner assignment
4. Insert via `insert_block` with pmBlock JSON:
   ```json
   {
     "type": "pmBlock",
     "attrs": {
       "blockType": "risk",
       "data": "{\"title\":\"Risk Register\",\"risks\":[{\"id\":\"r-1\",\"description\":\"...\",\"probability\":3,\"impact\":4,\"mitigation\":\"...\",\"strategy\":\"mitigate\",\"owner\":\"\"}]}",
       "version": 1
     }
   }
   ```

## Rules
- Score risks conservatively (err toward higher probability/impact)
- Always suggest at least one mitigation strategy per risk
- Color coding: green (1-6), yellow (7-12), red (13-25)
- Sort risks by score descending (highest risk first)
- Link to relevant issues when risks map to existing work items
