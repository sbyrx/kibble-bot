<script lang="ts">
  let status = $state('')
  let disabled = $state(false)

  async function dispense() {
    status = 'Dispensing kibbles...'
    disabled = true;

    const result = await fetch('/dispense', { method: 'GET' })
    const body:any = await result.json()

    status = body.status
    disabled = false
  }
</script>

<main>
  <h1>KibbleBot</h1>

  <button onclick={dispense} disabled={disabled}>
    Dispense
  </button>

  <p>{status}</p>
</main>
