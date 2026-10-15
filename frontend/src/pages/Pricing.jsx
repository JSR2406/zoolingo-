import { useEffect, useState } from 'react'
import {
  ArrowRight,
  Check,
  Crown,
  Sparkles,
  ShieldCheck,
  Clock,
  Phone,
} from 'lucide-react'
import { API_BASE } from '../App'
import { useToast } from '../components/Toast'

const inputClass =
  'w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-text-secondary focus:border-primary focus:outline-none'

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    priceSuffix: '',
    description: 'Get started with animal voice translation',
    conversionQuota: 2,
    conversionQuotaText: '2 total conversions (one-time allowance)',
    features: [
      'Basic animal sound translation',
      'Hindi + English TTS voices',
      'Standard processing',
    ],
    popular: false,
    buttonText: 'Get Started Free',
    buttonVariant: 'outline',
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 599,
    priceSuffix: '/month',
    description: 'For pet owners who need more translations',
    conversionQuota: null,
    conversionQuotaText: 'Unlimited conversions',
    features: [
      'Unlimited voice conversions',
      'Hindi + English + Hinglish TTS',
      'Priority processing',
      'Email support',
    ],
    popular: true,
    buttonText: 'Upgrade to Pro',
    buttonVariant: 'primary',
  },
  {
    id: 'premium',
    name: 'Premium',
    price: 1599,
    priceSuffix: '/month',
    description: 'For power users and multiple pets',
    conversionQuota: null,
    conversionQuotaText: 'Unlimited conversions',
    features: [
      'Unlimited voice conversions',
      'All Indian languages via SARVAM',
      'Priority processing + SLA',
      'Email + phone support',
      'Pet healthcare records',
      'Care reminders',
    ],
    popular: false,
    buttonText: 'Upgrade to Premium',
    buttonVariant: 'primary',
  },
]

export default function Pricing() {
  const toast = useToast()
  const [plans, setPlans] = useState(PLANS)
  const [loading, setLoading] = useState(true)
  const [selectedPlan, setSelectedPlan] = useState(null)

  useEffect(() => {
    // Fetch plans from backend (fallback to static PLANS if backend unavailable)
    async function fetchPlans() {
      try {
        const res = await fetch(`${API_BASE}/billing/plans`)
        if (res.ok) {
          const backendPlans = await res.json()
          // Map backend plans to frontend format
          const mapped = backendPlans.map((p) => ({
            id: p.id,
            name: p.name,
            price: p.price_monthly_inr,
            priceSuffix: '/month',
            description: `${p.features.join(', ')}`,
            conversionQuota: p.conversion_quota,
            conversionQuotaText:
              p.conversion_quota === null
                ? 'Unlimited conversions'
                : `${p.conversion_quota} total conversions`,
            features: p.features,
            popular: p.id === 'pro',
            buttonText: `Upgrade to ${p.name}`,
            buttonVariant: p.id === 'free' ? 'outline' : 'primary',
          }))
          setPlans(mapped)
        }
      } catch {
        // Fall back to static PLANS
      } finally {
        setLoading(false)
      }
    }
    fetchPlans()
  }, [])

  const handleSelectPlan = (plan) => {
    setSelectedPlan(plan)
  }

  const handleUpgrade = async (plan) => {
    if (!plan) return

    // In a real implementation, this would call /billing/checkout
    // and redirect to the checkout URL returned by the backend
    try {
      const res = await fetch(`${API_BASE}/billing/checkout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Authorization header would be set with the user's JWT
        },
        body: JSON.stringify({
          plan: plan.id,
          success_url: `${window.location.origin}/billing/success`,
          cancel_url: `${window.location.origin}/billing/cancel`,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        // Redirect to checkout URL
        window.location.href = data.checkout_url
      } else {
        const errorData = await res.json().catch(() => ({}))
        toast.error(
          'Checkout failed',
          errorData.detail || 'Unable to create checkout session'
        )
      }
    } catch (err) {
      toast.error('Checkout failed', err.message)
    }
  }

  const formatPrice = (price) => {
    if (price === 0) return 'Free'
    return `₹${price}`
  }

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="glass-panel-solid rounded-3xl p-8 text-center">
        <div className="flex items-center justify-center gap-2 mb-4">
          <Crown className="h-6 w-6 text-primary" />
          <h1 className="text-3xl font-bold gradient-text">Choose Your Plan</h1>
        </div>
        <p className="text-text-secondary text-lg max-w-2xl mx-auto">
          Simple, transparent pricing for pet voice translation. No hidden fees.
          Cancel anytime.
        </p>
      </div>

      {/* Plans */}
      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`glass-panel rounded-3xl p-6 relative ${
              plan.popular
                ? 'border-2 border-primary scale-105 z-10'
                : 'border border-white/10'
            }`}
          >
            {plan.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white text-xs font-bold px-3 py-1 rounded-full">
                Most Popular
              </div>
            )}
            <h2 className="text-2xl font-bold text-white mb-2">{plan.name}</h2>
            <div className="flex items-baseline gap-1 mb-4">
              <span className="text-4xl font-bold text-white">
                {plan.price === 0 ? 'Free' : `₹${plan.price}`}
              </span>
              <span className="text-text-muted">{plan.priceSuffix}</span>
            </div>
            <p className="text-text-secondary text-sm mb-6">
              {plan.conversionQuotaText}
            </p>

            <ul className="space-y-3 mb-8">
              {plan.features.map((feature, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <Check className="h-4 w-4 text-emerald-400" />
                  <span className="text-text-secondary">{feature}</span>
                </li>
              ))}
            </ul>

            <button
              onClick={() => {
                setSelectedPlan(plan)
                handleUpgrade(plan)
              }}
              className={`w-full py-3 rounded-xl font-bold text-sm transition-all ${
                plan.buttonVariant === 'primary'
                  ? 'bg-primary text-white hover:opacity-90'
                  : 'border border-white/20 text-white hover:bg-white/10'
              }`}
            >
              {plan.buttonText}
            </button>
          </div>
        ))}
      </div>

      {/* FAQ */}
      <div className="glass-panel rounded-3xl p-8">
        <h2 className="text-2xl font-bold text-white mb-6">Frequently Asked Questions</h2>
        <div className="space-y-3">
          <div className="border-b border-white/10 pb-3">
            <h3 className="font-semibold text-white text-sm">How does the free tier work?</h3>
            <p className="text-text-sm text-text-secondary">
              The free tier includes 2 voice conversions total (not per month).
              Once you've used both, you can upgrade to Pro or Premium for
              unlimited conversions.
            </p>
          </div>
          <div className="border-b border-white/10 pb-3">
            <h3 className="font-semibold text-white text-sm">Can I cancel anytime?</h3>
            <p className="text-text-sm text-text-secondary">
              Yes. You can cancel your subscription at any time. Your access
              continues until the end of your current billing period.
            </p>
          </div>
          <div className="border-b border-white/10 pb-3">
            <h3 className="font-semibold text-white text-sm">What payment methods are accepted?</h3>
            <p className="text-text-sm text-text-secondary">
              We accept credit/debit cards via Stripe (global) and Razorpay
              (India). All payments are processed securely on our partners'
              platforms.
            </p>
          </div>
          <div className="pb-3">
            <h3 className="font-semibold text-white text-sm">Are taxes included?</h3>
            <p className="text-text-sm text-text-secondary">
              Prices shown are in Indian Rupees (₹). Applicable taxes (GST)
              will be added at checkout based on your location.
            </p>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="glass-panel rounded-3xl p-6 border border-amber-500/30 bg-amber-500/10">
        <div className="flex items-start gap-3">
          <ShieldCheck className="h-5 w-5 text-amber-400 mt-0.5" />
          <div>
            <h3 className="font-semibold text-amber-300 text-sm">
              Important Disclaimer
            </h3>
            <p className="text-xs text-amber-200 mt-1">
              ZooLingo provides animal sound interpretation for educational and
              entertainment purposes. It is not a veterinary diagnostic tool.
              Always consult a qualified veterinarian for pet health concerns.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
