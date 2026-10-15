import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="max-w-xl py-16">
      <h1 className="text-2xl font-semibold">This page doesn't exist</h1>
      <p className="mt-2 text-ink-2">The link may be out of date. Go back to the overview to carry on.</p>
      <Link to="/" className="mt-4 inline-block font-medium text-petrol underline underline-offset-4">Open the executive overview</Link>
    </div>
  );
}
