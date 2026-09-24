// Placeholder home page. The real search UI arrives in build step 4.
export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-4 px-4 py-16">
      <p className="text-sm font-medium uppercase tracking-wide text-orange-600">
        Boston / Cambridge
      </p>
      <h1 className="text-4xl font-bold tracking-tight">Campus Eats</h1>
      <p className="text-lg text-zinc-600 dark:text-zinc-400">
        Great food, fair prices, ranked for students. Coming soon.
      </p>
    </main>
  );
}
