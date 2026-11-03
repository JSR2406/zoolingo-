# ZooLingo Implementation Audit Checklist

## Methodology
- ✅ = Implemented and verified working
- ⚠️ = Partially implemented or unverified
- ❌ = Missing entirely
- ⛔ = Blocked by credentials, hardware, data, or product decision

---

## 1. Authentication and Authorization ❌

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| User registration | ❌ | - | No auth exists | Signup, login, password hash, JWT | Add Auth0/Firebase/email-pwd adapter | Register, login, invalid creds |
| User login/session | ❌ | - | No sessions | JWT access + refresh tokens | Middleware to verify JWT on all stateful endpoints | Token expiry, refresh rotation |
| Password hashing | ❌ | - | No users table | bcrypt/argon2 integration | Server-side password storage | Hash strength, timing-safe compare |
| Ownership enforcement | ❌ | backend/app.py, petcare/ | No user_id on any table | Add user_id FK to pets, conversations, voice_conversions | Every endpoint filters by authenticated user | Cross-user access blocked |
| Row-level security | ❌ | backend/petcare/database.py | SQLite, no RLS | Enable RLS if Supabase, or app-level ownership checks | Add user_id to all tables, filter queries | Pet data isolation |
| API key security | ⚠️ | backend/.env | Keys in .env | Never commit secrets, use env only | Add .env.example without real values | No secrets in git |

---

## 2. Audio Recording, Upload, Preprocessing, Inference ⚠️

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Audio upload endpoint | ✅ | backend/app.py | /api/process-audio accepts WAV/MP3/etc | Add auth dependency, idempotency key, rate limit | Add Depends(get_current_user), idempotency header | Invalid file, oversize, rate limit |
| WebM/Opus mic support | ✅ | backend/services/audio_processor.py | PyAV decoding for webm/opus | Test with real browser recordings | Add duration limits, silence detection | Real mic upload, truncated file |
| Silence/non-audio rejection | ⚠️ | backend/services/audio_processor.py | Returns mock features for empty audio | Return 400 for silence/non-animal audio | Abstain on unsupported input | Silence file, white noise, speech |
| Model label order verification | ❌ | backend/services/ai_classifier.py | No training encoder available | Verify label mapping matches training | Document label order, add validation test | Model output vs expected labels |
| Temporal feature preservation | ⚠️ | backend/services/audio_processor.py | Onset count, pitch std included | Verify model was trained on same features | Document feature list, add unit test | Feature vector length = 55 |
| Dog/cat evaluation separation | ❌ | backend/services/ai_classifier.py | Single heuristic for all animals | Separate dog vs cat evaluation metrics | Add per-species test suite | Dog audio → Dog label, Cat audio → Cat label |
| Softmax ≠ calibrated confidence | ⚠️ | backend/services/ai_classifier.py | Heuristic score called "confidence" | Label as "interpretation_score" not calibrated | Rename field, add disclaimer in response | Response includes "interpretation_score" |
| Abstain on uncertain input | ❌ | backend/services/ai_classifier.py | Always returns a result | Return low_confidence/abstained when scores unclear | Add threshold, return abstained status | Ambiguous audio → abstained |
| Preprocessing matches training | ❌ | backend/services/audio_processor.py | No training config available | Document training sr/n_mfcc, add validation | Add feature config version, validate at startup | Feature config hash check |

---

## 3. Hindi, English, Hinglish Text and Speech Output ⚠️

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Hindi TTS (SARVAM Bulbul v3) | ✅ | backend/services/sarvam_integration.py | hi-IN voices: shubh, ritu, tanya | Verify SARVAM API format, test live | Test with actual SARVAM key | SARVAM API returns MP3 |
| English TTS | ✅ | backend/services/sarvam_integration.py | en-IN voices: neha, rohan | Same as Hindi | Test live | |
| Hinglish support | ❌ | backend/config.py | Only hi-IN, en-IN configured | No Hinglish code exists in SARVAM | Verify if SARVAM supports Hinglish, add if available | Hinglish text → TTS output |
| Hindi text translation | ✅ | backend/services/sarvam_llm.py | Sarvam-105B LLM translation | Verify actual API, test live | Add fallback if LLM unavailable | Hindi output for dog+happy |
| English text | ✅ | backend/services/nlp_translator.py | Deterministic English phrases | None needed | None | |
| Language selection UI | ✅ | frontend/src/components/LanguageSelector.jsx | hi-IN, en-IN buttons | Add Hinglish option if supported | Conditionally show Hinglish | UI renders language options |
| Per-language voice validation | ✅ | backend/services/sarvam_integration.py | validate_speaker rejects cross-lang | None needed | None | shubh on en-IN falls back to neha |

---

## 4. Subscription Management and Usage Enforcement ❌

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Free tier (2 conversions total) | ❌ | - | No usage tracking | subscriptions, usage_ledger, usage_reservations tables | Add plan config, quota enforcement | 2 free → 3rd blocked |
| Pro tier ₹599/month | ❌ | - | No pricing | Stripe/Razorpay adapter, webhook handler | Add pricing config, checkout flow | Pro activates after payment |
| Premium tier ₹1,599/month | ❌ | - | No pricing | Same as Pro | Same as Pro | Premium activates |
| Configurable quotas | ❌ | - | No quota system | Plan entitlement configuration table | Centralised plan config | Quota change takes effect |
| Fail-closed checkout | ❌ | - | No checkout | If paid entitlements not configured, block upgrade | Add config validation at startup | Missing config → error |
| Atomic reservation/finalisation | ❌ | - | No usage accounting | usage_reservations with status (pending/confirmed/released) | Reserve before conversion, finalise after success | Concurrent requests don't exceed free |
| Idempotency keys | ❌ | - | No idempotency | Idempotency-Key header on conversion endpoint | Store key+result, return cached on duplicate | Duplicate key → same result |
| Consume only after success | ❌ | backend/app.py | No usage tracking | Consume conversion only after TTS success | Move usage deduction to after audio generated | Failed conversion → no charge |
| Release after failure/timeout | ❌ | - | No reservation system | Release reserved conversions on error/timeout | Reservation TTL, cleanup job | Timeout → reservation released |
| Pricing page | ❌ | frontend/src/pages/ | No pricing page | Create Pricing.jsx | Add Free/Pro/Premium cards | Page renders prices |
| Upgrade flow | ❌ | - | No upgrade | Checkout redirect, webhook processing | Add Stripe/Razorpay integration | Sandbox mode works |
| Current plan/usage display | ❌ | - | No plan context | Add plan to user profile, usage counter | Show in header/dashboard | Usage: "2/2 free used" |
| Billing status view | ❌ | - | No billing UI | Add billing page | Show subscription status, next billing | Page loads without auth error |
| Cancellation management | ❌ | - | No cancellation | Stripe/Razorpay cancel subscription | Add cancel button, confirm dialog | Cancel → plan reverts to free |
| Payment error states | ❌ | - | No error handling | Add error UI for declined cards, webhook failures | Toast/inline errors | Decline → error message |
| Tax policy documentation | ❌ | - | No tax info | Document whether prices include tax | Add note on pricing page | Tax policy stated |

---

## 5. Pet Profiles and Persistent Chat History ⚠️

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Pet profile CRUD | ✅ | backend/petcare/ | SQLite pets table | Add user_id FK, photo URL, owner reference | Add user_id to pets, enforce ownership | Cross-user pet access blocked |
| Species: dog/cat only | ⚠️ | backend/petcare/database.py | 15+ animals supported | Restrict to dog/cat for MVP per spec | Validate species in {dog, cat} | Invalid species → 400 |
| Multiple conversations per pet | ❌ | - | No conversations table | conversations table with pet_id FK | Add conversations, sessions | Create, list, rename, delete |
| Persist user + assistant messages | ❌ | - | Expert chat is stateless | messages table with role, content, timestamps | Add messages, link to conversation | CRUD messages |
| Persist voice-conversion events | ❌ | - | No voice_conversions table | voice_conversions with text, language, model_version, status | Add table, link to conversation | Conversion event stored |
| Model scores separate from confidence | ❌ | backend/app.py | Returns "confidence" field | Store raw model score + calibrated separately | Add interpretation_score, confidence fields | DB has both fields |
| Preserve uncertainty/refusal | ❌ | backend/app.py | Always returns result | Store abstained/unknown outcomes | Add status field (success/abstained/failed) | Abstained → status stored |
| Search/paginate history | ❌ | - | No history endpoints | Add GET /api/conversations with pagination | Add search, limit/offset | Page 2 returns different results |
| Rename/delete/export conversations | ❌ | - | No conversation management | PUT/DELETE/GET export endpoints | Add management endpoints | Delete removes all messages |
| Replay retained audio | ❌ | - | Audio stored as temp files | audio_assets table, signed URLs | Store object ID, generate signed URL on demand | Signed URL expires, plays audio |
| Loading/retry/empty/failure states | ⚠️ | frontend/src/pages/ | Some states exist | Add consistent states across all pages | Standardise error/loading UI | Error state shows retry button |
| Text chat support | ❌ | frontend/src/pages/Expert.jsx | Voice-only expert | Add text input alongside voice | Add text message input | Text message sends and receives |
| User identity from verified auth | ❌ | - | No auth | Derive user_id from JWT, not request params | Middleware extracts user_id | Missing JWT → 401 |
| Never trust user_id in params | ❌ | backend/petcare/router.py | No auth checks | Remove user_id from request params, use JWT | All endpoints use authenticated user | user_id param ignored |

---

## 6. LangGraph Agent Integration ❌

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| LangGraph installed | ❌ | backend/requirements*.txt | No langgraph | pip install langgraph langchain | Add to requirements | Import works |
| Typed graph state | ❌ | - | No graph | Define State with messages, user_id, pet_id, intent, tool_calls | Create state Pydantic models | State serialises |
| Strict tool schemas | ❌ | - | expert_engine is free-form | Pydantic input/output for each tool | Create tool schemas | Invalid input → validation error |
| User/pet/conversation-scoped persistence | ❌ | - | No checkpointer | SqliteSaver or PostgresSaver | Add persistent checkpointer | Conversation survives restart |
| Bounded conversation memory | ❌ | - | No memory window | Limit to N recent messages | Add memory trim | Old messages dropped |
| Timeouts, retries, recursion limits | ❌ | - | No limits | Add timeout config, max_retries, max_recursion | Configure graph limits | Recursion → error |
| Tool-level authorization | ❌ | - | No tool auth | Each tool checks user owns pet | Add auth decorator in tools | Unauthorized tool → 403 |
| Structured logging + redaction | ❌ | - | Basic logging | Redact PII, payment keys, tokens | Add logging middleware | Logs don't contain secrets |
| Graceful unavailable integration | ⚠️ | backend/petcare/expert_engine.py | Rule-based fallback | Add integration status flags | Return degraded gracefully | SARVAM down → rule-based works |
| Injection-resistant external content | ❌ | - | No sanitisation | Sanitize tool results, escape HTML | Add sanitization in tool outputs | XSS attempt → neutralised |
| Explicit confirmation for writes | ❌ | - | No confirmation flow | agent_action_confirmations table | Require confirm before health/reminder changes | Changed args → new confirmation |
| Confirmation bound to exact action | ❌ | - | No confirmation | Store proposed action hash, verify on execute | Hash action params, compare on execution | Modified params → reject |
| LLM doesn't diagnose/prescribe | ✅ | backend/petcare/expert_engine.py | Rule-based, no diagnosis | None needed | Add system prompt disclaimer | LLM output contains disclaimer |
| LLM doesn't invent locations | ❌ | - | No location feature | Add disclaimer, validate against tracker data | Add validation | No fake locations |

---

## 7. GPS and Location Tracking ❌

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Location-provider adapter | ❌ | - | No location code | Abstract adapter interface | Create LocationProvider base class | Adapter pattern test |
| Tracker registration | ❌ | - | No tracker code | tracker_devices, pet_locations tables | Add registration endpoint | Register, list trackers |
| Secure device auth | ❌ | - | No auth | API key per device, signature validation | Add device auth middleware | Invalid key → 401 |
| Location ingestion | ❌ | - | No ingestion | POST /api/locations endpoint | Accept coordinates, accuracy, timestamps | Valid location stored |
| Last-seen + freshness | ❌ | - | No location data | Compute freshness from recorded_at | Add freshness indicator | Stale → "stale" label |
| Location history + pagination | ❌ | - | No history | GET /api/locations/pet/{id} with limit/offset | Add pagination | Page 2 returns older |
| Map view | ❌ | frontend/src/pages/ | No map component | Add map page (Leaflet/Mapbox) | Add MapPage.jsx | Map renders markers |
| Optional geofences | ❌ | - | No geofence code | geofences table, alert logic | Add geofence CRUD, alert deduplication | Enter geofence → alert once |
| Location-sharing permissions | ❌ | - | No permissions | Add sharing config per pet | Add share toggle | Sharing off → no location |
| "No pet tracker connected" | ❌ | - | No tracker UI | Show message when no tracker | Add empty state | No tracker → message shown |
| Development simulator | ❌ | - | No simulator | Add clearly labelled sim mode | Add simulator toggle | Simulated → "SIMULATED" badge |
| Geofence hysteresis/debounce | ❌ | - | No geofence logic | Add debounce window, accuracy check | Add hysteresis config | Single bad sample → no alert |
| Unknown/stale location honest | ❌ | - | No location data | Return "unknown" or "stale" | Add status field | No data → "unknown" |
| No continuous tracking claim | ✅ | - | No tracking implemented | None needed | Document limitation | |

---

## 8. Pet Healthcare Tracking ⚠️

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Vaccinations + due dates | ✅ | backend/petcare/ | vaccination_records table | Add user_id FK, ownership checks | Add user_id, enforce | Cross-user blocked |
| Vet appointments | ❌ | - | No appointments table | appointments table | Add appointment CRUD | Create, list, cancel |
| Medication schedules | ❌ | - | No medication table | medication_schedules table | Add medication CRUD | Create, list, update |
| Weight logs with units | ✅ | backend/petcare/ | weight_log table | Add user_id FK | Add user_id | Ownership enforced |
| Allergies and conditions | ❌ | - | No allergies table | allergies table | Add allergy CRUD | Create, list |
| Symptom observations | ❌ | - | No symptom table | symptom_observations table | Add symptom CRUD | Create, list |
| Vet documents/prescriptions | ❌ | - | No document storage | documents table, private storage | Add upload, signed URLs | Upload, download |
| Care reminders | ⚠️ | backend/petcare/ | care_schedules table | Add reminder delivery, timezone | Add reminder_deliveries table | Reminder stored, delivered |
| Owner vs clinician vs AI distinction | ❌ | - | No source tracking | Add source field to all health tables | source: owner/clinician/ai | Query by source |
| Health observations separate from classification | ✅ | backend/petcare/ | Separate tables | None needed | Keep separate | No mixing |
| No diagnosis from vocalisation | ✅ | backend/app.py | Returns interpretation only | None needed | Add disclaimer in response | Response has disclaimer |
| No medication doses from AI | ✅ | backend/petcare/expert_engine.py | Rule-based, no doses | None needed | Add system prompt | |
| Document provenance + timestamps | ❌ | - | No document table | created_at, updated_at, uploaded_by | Add fields | |
| Private storage + validated uploads | ❌ | - | No file storage | Add S3/private bucket, validate file types | Add upload endpoint | Invalid type → 400 |
| Correction/deletion/export | ❌ | - | Some DELETE exists | Add full CRUD + export endpoint | Add PATCH, DELETE, GET export | Export returns JSON |
| Confirmation before AI changes | ❌ | - | No confirmation | agent_action_confirmations table | Require confirm for AI-suggested changes | Unconfirmed → not applied |
| "Not a replacement for vet care" | ❌ | - | No disclaimer | Add to UI and API responses | Add disclaimer everywhere | Footer shows disclaimer |

---

## 9. Clinic and Brand Partnerships ⚠️

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Vet clinic listings | ✅ | backend/petcare/ | vet_contacts table | Add user_id, status, moderation | Add status field, admin review | Unmoderated → hidden |
| Pet-care brand/product listings | ❌ | - | No products table | partners, products tables | Add product CRUD | Create, list |
| Referral links/booking requests | ❌ | - | No referral code | referrals table with attribution | Add referral generation, tracking | Click tracked |
| Commission tracking | ❌ | - | No commission | commissions table (pending/confirmed/reversed/settled) | Add commission CRUD | Status transitions |
| Sponsored placements | ❌ | - | No sponsorship | Add is_sponsored flag | Add flag, label in UI | Sponsored → labelled |
| Admin partner management | ❌ | - | No admin UI | Add partner CRUD with status | Add admin endpoints | Admin can approve/reject |
| Partner status/moderation | ❌ | - | No moderation | status: pending/approved/rejected | Add moderation flow | Rejected → not shown |
| Configurable commission rules | ❌ | - | No rules | commission_rules table | Add rule engine | Rule change applies |
| Referral/conversion attribution | ❌ | - | No attribution | Track referrer_id on conversions | Add attribution | Click → conversion linked |
| Commission status transitions | ❌ | - | No commission | pending → confirmed → reversed → settled | Add state machine | Invalid transition → error |
| Refund/cancellation handling | ❌ | - | No refunds | Add refund tracking | Add refund endpoint | Refund → commission reversed |
| Audit logs | ❌ | - | No audit | audit_events table | Log all partner changes | Log queryable |
| No "Booking confirmed" without provider | ✅ | - | No booking implemented | None needed | Only show confirmed after provider API | |
| Commercial separate from health | ✅ | - | No mixing | None needed | Keep separate UI sections | |

---

## 10. Cloud Architecture and Performance ⚠️

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Cloud-based, no offline | ✅ | - | FastAPI + Vercel | None needed | None | |
| Load model once per worker | ⚠️ | backend/app.py | Global classifier instance | Verify TensorFlow loads once | Add startup event | Model loaded at startup |
| Measure latency stages | ❌ | backend/app.py | Only total duration | Add per-stage timing | Add timing middleware | Log shows each stage |
| Report observed latency | ❌ | - | No latency reporting | Add latency to health endpoint | Add /api/latency | Returns p50/p95 |
| No unnecessary agent calls | ✅ | backend/app.py | Direct service call | None needed | Keep direct | |
| Bounded concurrency/backpressure | ❌ | - | No limits | Add semaphore, queue | Add max_concurrent | Over limit → 429 |
| Rate limits + size/duration limits | ⚠️ | backend/app.py | MAX_UPLOAD_SIZE=10MB | Add rate limiting per user | Add slowapi/redis rate limit | Over limit → 429 |
| Cache speech outputs | ❌ | - | No caching | Add Redis cache keyed by text+lang+voice | Add cache layer | Same input → cache hit |
| Redis failure doesn't break core | ❌ | - | No Redis | Wrap cache in try/except | Fail open | Redis down → works |
| Background jobs use serializable IDs | ❌ | - | No background jobs | Add Celery/ARQ/RQ | Add task queue | Job returns ID |
| Job status secured by ownership | ❌ | - | No job endpoints | Add GET /api/jobs/{id} with auth | Secure endpoints | Other user → 403 |
| No sequential loop = batching | ✅ | - | No false batching | None needed | None | |

---

## 11. Database and API Design ⚠️

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Versioned migrations | ❌ | - | SQLite, no migrations | Add Alembic or manual migration files | Add migration system | Migration applies cleanly |
| Foreign keys + indexes | ⚠️ | backend/petcare/database.py | Some FKs exist | Add all missing FKs, indexes on user_id, pet_id | Add indexes | Query performance |
| Ownership constraints | ❌ | - | No user_id anywhere | Add user_id to all tables | Add user_id, enforce in queries | Cross-user → 404 |
| Unique idempotency keys | ❌ | - | No idempotency | unique constraint on idempotency_key | Add constraint | Duplicate → error |
| Explicit status transitions | ❌ | - | Implicit status | Add status enum, transition validation | Add state machine | Invalid → 400 |
| UTC storage + timezone presentation | ❌ | backend/petcare/database.py | Uses datetime('now') | Store UTC, convert on read | Add timezone handling | Display in user tz |
| Consistent API errors | ⚠️ | backend/app.py | JSONResponse with status | Add standard error format | Add error model | Error has code+message |
| Pagination | ❌ | - | No pagination | Add limit/offset to list endpoints | Add pagination params | Page 2 returns next set |
| Input validation | ✅ | backend/app.py | Pydantic schemas | Extend to all endpoints | Add validation | Invalid → 422 |
| Backward compatibility | ❌ | - | No versioning | Add /api/v1/ prefix | Add versioning | /api/v1/ works |

---

## 12. Frontend Requirements ⚠️

| Item | Status | Files | Current Behaviour | Missing Work | Planned Changes | Tests Needed |
|------|--------|-------|-------------------|--------------|-----------------|--------------|
| Pricing and billing | ❌ | - | No pricing page | Create Pricing.jsx | Add Free/Pro/Premium | Page renders |
| Usage allowance display | � | - | No usage UI | Add usage counter | Show "X/Y conversions used" | Counter updates |
| Pet-profile selector | ✅ | frontend/src/pages/Health.jsx | Pet dropdown | Works | None | |
| Persistent chat interface | ❌ | frontend/src/pages/Expert.jsx | Stateless SSE | Add conversation list, message history | Add conversation UI | Messages persist |
| Searchable history | ❌ | - | No search | Add search input | Filter conversations | Search returns matches |
| Hindi/English/Hinglish | ✅ | frontend/src/components/LanguageSelector.jsx | hi-IN, en-IN | Add Hinglish if supported | Conditional option | UI shows option |
| Pet healthcare dashboard | ✅ | frontend/src/pages/Health.jsx | Vaccinations, weights, records | Works | None | |
| Reminder management | ⚠️ | frontend/src/pages/CareSchedules.jsx | Care schedules exist | Add reminder delivery status | Add delivery status | |
| Location map + tracker | ❌ | - | No map | Add map page | Add MapPage.jsx | |
| Clinic/product directory | ⚠️ | frontend/src/pages/VetDirectory.jsx | Vet directory exists | Add products | Add product cards | |
| Privacy/consent/export/deletion | ❌ | - | No privacy UI | Add privacy page | Add consent, export, delete | |
| Mobile-responsive | ✅ | frontend/ | Tailwind CSS | None needed | None | |
| Accessible controls | ⚠️ | frontend/ | Basic ARIA | Add more ARIA labels | Improve accessibility | |
| Loading/error states | ✅ | frontend/ | Some states exist | Standardise across pages | Add consistent states | |
| No "implemented" badge unless verified | ⚠️ | README.md | Claims production ready | Remove unsupported claims | Update README | |
| No fabricated charts/partners | ✅ | frontend/ | No fake data | None needed | None | |

---

## 13. Credentials, Hardware, Data, Decisions Still Required

| Item | Required For | Notes |
|------|--------------|-------|
| Supabase URL + Service Role Key | Pet data persistence | Set in Render env vars |
| Stripe/Razorpay API keys | Subscription billing | Sandbox mode for testing |
| SARVAM API Key | Hindi/English TTS | Already in .env locally |
| Mapbox/Leaflet key | Location map | Free tier available |
| TensorFlow model weights | ML classification | Currently using heuristic fallback |
| Training data (dog/cat audio) | Model training | Currently using generated fixtures |
| Production database | Production deployment | SQLite → PostgreSQL migration |
| Animal adoption marketplace data | Marketplace feature | Not yet designed |
| Tax policy decision | Pricing page | Include or add tax? |
| Payment provider choice | Subscriptions | Stripe vs Razorpay (India-focused) |

---

## Implementation Order

1. **Stage 1**: Authentication + Core audio flow fixes (fix core authenticated audio→interpretation→speech)
2. **Stage 2**: Subscription plans + usage enforcement
3. **Stage 3**: Pet profiles + persistent chat history
4. **Stage 4**: LangGraph agent integration
5. **Stage 5**: GPS/location tracking
6. **Stage 6**: Pet healthcare tracking + reminders
7. **Stage 7**: Clinic/brand partnerships
8. **Stage 8**: Animal adoption marketplace (ideation + plan)

---
