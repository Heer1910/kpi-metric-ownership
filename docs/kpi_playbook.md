# KPI Playbook

**Purpose:** Operational guide for using and acting on KPI movements.

**Audience:** Product managers, business analysts, leadership

**Last Updated:** 2026-01-20

---

## 🎯 Quick Reference

### North Star: VPAC

**What it is:** Value per Active Customer = Orders per Customer × Items per Order

**Why it matters:** Captures the combined effect of purchase frequency and basket depth, both key drivers of business value.

**Good/Bad:**
- ✅ **Good:** Increasing VPAC means customers are ordering more frequently AND/OR buying more per order
- ⚠️ **Warning:** Flat VPAC while active customers are growing fast → may be acquiring lower-quality users
- ❌ **Bad:** Declining VPAC → retention problem OR merchandising problem

---

## 📊 How to Read the Metrics

### VPAC Components

#### Orders per Customer (Purchase Frequency)

**What moves it:**
- Retention initiatives
- Lifecycle marketing (email, push)
- Product improvements (faster checkout, saved carts)
- Loyalty programs

**How to interpret changes:**

| Movement | Likely Cause | Action |
|----------|-------------|--------|
| ↗️ Increasing | Better retention, successful lifecycle campaigns | Double down on what's working |
| ↘️ Decreasing | Losing repeat purchasers, competitive pressure | Investigate retention cohorts, survey lapsed users |
| Flat while customers grow | Acquiring one-time buyers | Improve onboarding, first-order experience |

#### Items per Order (Basket Depth)

**What moves it:**
- Merchandising (recommendations, cross-sell)
- Product catalog changes
- UX improvements (search, browse)
- Pricing/promotions

**How to interpret changes:**

| Movement | Likely Cause | Action |
|----------|-------------|--------|
| ↗️ Increasing | Better merchandising, effective cross-sell | Scale successful tactics |
| ↘️ Decreasing | Poor product discovery, catalog issues | A/B test new recommendation algo, audit search |
| Volatile | Seasonal or promotional effects | Decompose by category, check for outliers |

---

## 🔍 Diagnostic Workflow

When VPAC moves, follow this process:

### Step 1: Decompose the Change

Run the decomposition analysis to attribute change:

```
Δ VPAC = (Δ Orders per Customer × avg Items per Order) + (avg Orders per Customer × Δ Items per Order) + Interaction
```

**Question to answer:** Which driver contributed more to the change?

### Step 2: Segment Analysis

**If Orders per Customer moved:**
- Segment by customer cohort (new vs returning)
- Check reorder rate by cohort
- Investigate median days between orders

**If Items per Order moved:**
- Segment by product category
- Check for changes in small basket share
- Audit recommendation engine performance

### Step 3: Validate with Guardrails

Check guardrail metrics to ensure quality:

| Guardrail | Red Flag | Action |
|-----------|----------|--------|
| Small Basket Share | >30% | Investigate acquisition quality, improve first-order UX |
| Median Days Between Orders | Increasing trend | Retention issue, increase lifecycle marketing |
| Reorder Rate | Decreasing | Product quality concern, survey customers |

### Step 4: Look for Anomalies

- Are there outlier days/weeks?
- Any data quality issues?
- External events (holidays, promotions, outages)?

---

## 🎯 Recommended Actions by Scenario

### Scenario 1: VPAC Increasing (Good!)

**Validation:**
- ✅ Check that both active customers AND VPAC are growing
- ✅ Verify guardrails are healthy (small basket share stable, reorder rate up)

**Actions:**
1. Document what changed (new feature, campaign, etc.)
2. Share learnings with broader team
3. Consider scaling successful tactics

---

### Scenario 2: VPAC Flat While Active Customers Growing

**Diagnosis:** Acquiring lower-quality users

**Actions:**
1. Segment new users by acquisition channel
2. Measure first-order quality (items, reorder rate) by channel
3. Tighten targeting on low-performing channels
4. Improve new user onboarding

---

### Scenario 3: VPAC Declining

**Diagnosis:** Retention problem OR merchandising problem

**Actions:**

**If driven by Orders per Customer ↘️:**
1. Cohort analysis: are recent cohorts worse, or are old cohorts churning?
2. Survey lapsed users
3. Increase win-back campaigns
4. Audit product/checkout UX for friction

**If driven by Items per Order ↘️:**
1. Check for catalog changes (products removed, out of stock)
2. A/B test new recommendation algorithms
3. Review search and browse analytics
4. Check for pricing issues

---

## 📅 Weekly Review Checklist

Use this checklist in your weekly business review:

- [ ] **North Star Check:** Is VPAC moving in the right direction?
- [ ] **Decomposition:** Which driver contributed most to change?
- [ ] **Guardrails:** Are small basket share and median days between orders healthy?
- [ ] **Segments:** Are any customer segments significantly different?
- [ ] **Anomalies:** Any unusual spikes or drops?
- [ ] **Data Quality:** Any missing data or validation failures?
- [ ] **Action Items:** What concrete actions will we take this week?

---

## 🚨 Alert Thresholds

Set up automated alerts for:

| Metric | Threshold | Severity |
|--------|-----------|----------|
| VPAC week-over-week change | < -5% | High |
| Small Basket Share | > 30% | Medium |
| Reorder Rate week-over-week change | < -3% | Medium |
| Active Customers week-over-week change | < -2% | High |

---

## 🔧 Troubleshooting

### "My VPAC moved but I don't know why"

1. Run decomposition to see which driver moved
2. Drill into that driver by segment
3. Check for data quality issues
4. Look for correlated external events

### "My metrics don't add up"

1. Check decomposition validation (should sum to total within 1%)
2. Verify monotonic relationships (orders >= customers, items >= orders)
3. Run data quality checks

### "I want to test a new initiative"

1. Define which metric(s) you expect to move
2. Set up a baseline measurement
3. Run experiment
4. Measure impact using decomposition

---

## 📚 Additional Resources

- [Metric Dictionary](./metric_dictionary.md) - Complete metric definitions
- [Weekly Business Review Template](../reports/weekly_business_review.md)
- [Data Quality Checks](../tests/) - Validation scripts

---

## 🤝 Metric Ownership & Escalation

| Metric | Primary Owner | Escalation Contact |
|--------|---------------|-------------------|
| VPAC | Product Growth Lead | VP Product |
| Active Customers | Marketing Lead | CMO |
| Orders per Customer | Retention PM | Product Growth Lead |
| Items per Order | Merchandising PM | Product Growth Lead |

---

*This playbook is a living document. Update as you learn more about your business drivers.*
