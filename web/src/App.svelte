<script lang="ts">
  let status = ''
  let disabled = false

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

  <button on:click={dispense} disabled={disabled}>
    Dispense
  </button>

  <p>{status}</p>
</main>
