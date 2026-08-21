import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

import { fetchBeacon, HttpCachingChain, HttpChainClient } from 'drand-client'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const packageMetadata = JSON.parse(
  fs.readFileSync(path.join(scriptDir, 'node_modules', 'drand-client', 'package.json'), 'utf8')
)

if (process.argv.length !== 4) {
  throw new Error('usage: node fetch_verified_beacon.mjs CONFIG_JSON OUT_JSON')
}

const config = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const chain = config.drand
const round = Number(chain.round)
if (!Number.isSafeInteger(round) || round < 1) {
  throw new Error('configured drand round is invalid')
}

const options = {
  disableBeaconVerification: false,
  noCache: true,
  chainVerificationParams: {
    chainHash: chain.chain_hash,
    publicKey: chain.public_key
  }
}
const relays = [...chain.relays]
if (relays.length < 3) {
  throw new Error('at least three preregistered drand relays are required')
}

const results = await Promise.all(relays.map(async (relay) => {
  const url = `${relay.replace(/\/$/, '')}/${chain.chain_hash}`
  const client = new HttpChainClient(new HttpCachingChain(url, options), options)
  const beacon = await fetchBeacon(client, round)
  return {
    relay,
    round: beacon.round,
    randomness: beacon.randomness,
    signature: beacon.signature,
    previous_signature: beacon.previous_signature ?? null
  }
}))

const identity = JSON.stringify({
  round: results[0].round,
  randomness: results[0].randomness,
  signature: results[0].signature,
  previous_signature: results[0].previous_signature
})
for (const result of results) {
  const observed = JSON.stringify({
    round: result.round,
    randomness: result.randomness,
    signature: result.signature,
    previous_signature: result.previous_signature
  })
  if (observed !== identity) {
    throw new Error('cryptographically verified drand relays disagree')
  }
}

const report = {
  schema_version: '1.0.0',
  status: 'CRYPTOGRAPHICALLY_VERIFIED_MULTI_RELAY_AGREEMENT',
  chain_hash: chain.chain_hash,
  public_key: chain.public_key,
  scheme_id: chain.scheme_id,
  round,
  randomness: results[0].randomness,
  signature: results[0].signature,
  previous_signature: results[0].previous_signature,
  relays: results.map((result) => result.relay),
  agreeing_relays: results.length,
  verification: {
    library: 'drand-client',
    version: packageMetadata.version,
    disable_beacon_verification: false,
    chain_verification_parameters_hardcoded_from_commitment: true
  }
}
fs.writeFileSync(process.argv[3], `${JSON.stringify(report, null, 2)}\n`, { encoding: 'utf8' })
process.stdout.write(`${JSON.stringify({
  status: report.status,
  round: report.round,
  agreeing_relays: report.agreeing_relays,
  verification_library: `${report.verification.library}@${report.verification.version}`
})}\n`)
