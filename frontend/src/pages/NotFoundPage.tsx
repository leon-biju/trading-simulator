import PageWrapper from '@/components/layout/PageWrapper'

export default function NotFoundPage() {
  return (
    <PageWrapper>
      <div className="flex min-h-[calc(100svh-7rem)] flex-col items-center justify-center">

        <span className="mb-8 select-none font-mono text-[120px] font-bold leading-none tracking-tighter text-edge lg:text-[160px]">
          404
        </span>

        <div className="text-center">
          <h1 className="mb-2 text-xl font-semibold text-bright">Page not found</h1>
        </div>

      </div>
    </PageWrapper>
  )
}
