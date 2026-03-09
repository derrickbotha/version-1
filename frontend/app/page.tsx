import HeroSection from '@/components/sections/HeroSection'
import TrustSection from '@/components/sections/TrustSection'
import PricingCalculator from '@/components/sections/PricingCalculator'
import ServicesSection from '@/components/sections/ServicesSection'
import ResearchDatabases from '@/components/sections/ResearchDatabases'
import ResearchProcess from '@/components/sections/ResearchProcess'
import WriterExpertise from '@/components/sections/WriterExpertise'
import HowItWorks from '@/components/sections/HowItWorks'
import QualityAssurance from '@/components/sections/QualityAssurance'
import Testimonials from '@/components/sections/Testimonials'
import FinalCTA from '@/components/sections/FinalCTA'

export default function HomePage() {
  return (
    <main>
      <HeroSection />
      <TrustSection />
      <ServicesSection />
      <PricingCalculator />
      <ResearchDatabases />
      <ResearchProcess />
      <WriterExpertise />
      <HowItWorks />
      <QualityAssurance />
      <Testimonials />
      <FinalCTA />
    </main>
  )
}
