"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { getPricing, checkoutStripe, checkoutPaypal, getOrders } from "@/lib/api";
import toast from "react-hot-toast";
import { CreditCard, ShoppingBag, CheckCircle, Zap, ArrowRight } from "lucide-react";
import clsx from "clsx";

function BillingContent() {
  const params      = useSearchParams();
  const router      = useRouter();
  const assignmentId = params.get("assignment_id");
  const reviewType   = params.get("review_type") ?? "agent_only";

  const [pricing, setPricing]       = useState<any>(null);
  const [orders, setOrders]         = useState<any[]>([]);
  const [loading, setLoading]       = useState(true);
  const [paying, setPaying]         = useState(false);
  const [selectedPlan, setSelected] = useState("professional");

  useEffect(() => {
    Promise.all([getPricing(), getOrders()])
      .then(([p, o]) => { setPricing(p); setOrders(o); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleStripe() {
    if (!assignmentId) {
      toast.error("No assignment selected. Create an assignment first.");
      return;
    }
    setPaying(true);
    try {
      const { checkout_url } = await checkoutStripe(assignmentId, reviewType);
      window.location.href = checkout_url;
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? "Stripe checkout failed");
    } finally {
      setPaying(false);
    }
  }

  async function handlePaypal() {
    if (!assignmentId) {
      toast.error("No assignment selected");
      return;
    }
    setPaying(true);
    try {
      const { checkout_url } = await checkoutPaypal(assignmentId, reviewType);
      window.location.href = checkout_url;
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? "PayPal checkout failed");
    } finally {
      setPaying(false);
    }
  }

  if (loading) return (
    <div className="flex h-screen items-center justify-center">
      <div className="animate-spin w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full" />
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-surface">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Billing & Plans</h1>
            <p className="text-gray-500 mt-1">Choose the plan that matches your academic level.</p>
          </div>

          {/* Pricing table */}
          {pricing && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
              {pricing.plans.map((plan: any) => {
                const sel = selectedPlan === plan.id;
                return (
                  <button
                    key={plan.id}
                    onClick={() => setSelected(plan.id)}
                    className={clsx(
                      "card text-left transition-all",
                      sel ? "border-brand-500 shadow-lg ring-2 ring-brand-200" : "hover:border-gray-300"
                    )}
                  >
                    {sel && (
                      <div className="flex justify-end mb-2">
                        <CheckCircle className="w-4 h-4 text-brand-600" />
                      </div>
                    )}
                    <p className={clsx("font-bold text-lg", sel ? "text-brand-700" : "text-gray-900")}>
                      {plan.price ? `$${plan.price}` : "Custom"}
                    </p>
                    <p className="text-xs text-gray-500 mb-0.5">/month</p>
                    <p className="font-semibold text-sm text-gray-800 mt-2">{plan.name}</p>
                    <p className="text-xs text-gray-500 mb-3">{plan.level}</p>
                    <ul className="space-y-1">
                      {plan.features.map((f: string) => (
                        <li key={f} className="text-xs text-gray-600 flex items-start gap-1">
                          <Zap className="w-3 h-3 text-brand-400 mt-0.5 flex-shrink-0" />
                          {f}
                        </li>
                      ))}
                    </ul>
                  </button>
                );
              })}
            </div>
          )}

          {/* Professor add-on info */}
          {pricing && (
            <div className="card mb-8 bg-orange-50 border-orange-200">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <CheckCircle className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="font-semibold text-orange-800">Professor Review Add-on — $20/assignment</p>
                  <p className="text-sm text-orange-700 mt-1">
                    {pricing.addons[0]?.description}. Selected review type: <strong>{reviewType.replace("_", " ")}</strong>.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Checkout section */}
          {assignmentId && (
            <div className="card mb-8">
              <h2 className="font-semibold text-gray-900 mb-4">Complete Your Order</h2>
              <p className="text-sm text-gray-500 mb-5">
                Assignment ID: <code className="text-xs bg-gray-100 px-2 py-0.5 rounded">{assignmentId}</code> ·
                Review: <strong>{reviewType.replace("_", " ")}</strong>
              </p>
              <div className="flex gap-4">
                <button
                  onClick={handleStripe}
                  disabled={paying}
                  className="btn-primary flex items-center gap-2 flex-1 justify-center"
                >
                  {paying ? (
                    <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    <>
                      <CreditCard className="w-4 h-4" />
                      Pay with Card (Stripe)
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
                <button
                  onClick={handlePaypal}
                  disabled={paying}
                  className="btn-secondary flex items-center gap-2 flex-1 justify-center"
                >
                  🅿️ Pay with PayPal
                </button>
              </div>
            </div>
          )}

          {/* Order history */}
          <div>
            <h2 className="font-semibold text-gray-900 mb-4">Order History</h2>
            {orders.length === 0 ? (
              <div className="card text-center py-10">
                <ShoppingBag className="w-10 h-10 text-gray-200 mx-auto mb-3" />
                <p className="text-gray-400 text-sm">No orders yet.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {orders.map((o: any) => (
                  <div key={o.id} className="card flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm text-gray-900">{o.description ?? "ASA Assignment"}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{new Date(o.created_at).toLocaleDateString()}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-gray-900">${Number(o.amount).toFixed(2)}</span>
                      <span className={clsx("badge",
                        o.status === "paid" ? "bg-green-100 text-green-700" :
                        o.status === "pending" ? "bg-yellow-100 text-yellow-700" :
                        "bg-red-100 text-red-700"
                      )}>
                        {o.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center">Loading...</div>}>
      <BillingContent />
    </Suspense>
  );
}
