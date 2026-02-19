#include <stdio.h>
#include <stdint.h>
#include <oqs/oqs.h>

int main(void) {
    /* 1️⃣ Create ML-DSA verifier */
    OQS_SIG *sig = OQS_SIG_new("ML-DSA-44");
    if (sig == NULL) {
        fprintf(stderr, "ERROR: ML-DSA-44 not supported\n");
        return 1;
    }

    /* 2️⃣ Load public key */
    uint8_t pk[sig->length_public_key];

    FILE *fpk = fopen("pqc_keys/sender_dilithium_pk.bin", "rb");
    if (!fpk) {
        fprintf(stderr, "ERROR: Could not open public key file\n");
        OQS_SIG_free(sig);
        return 1;
    }

    fread(pk, 1, sizeof(pk), fpk);
    fclose(fpk);

    /* 3️⃣ Load signature */
    uint8_t signature[sig->length_signature];
    size_t sig_len;

    FILE *fs = fopen("pqc_keys/signature.bin", "rb");
    if (!fs) {
        fprintf(stderr, "ERROR: Could not open signature file\n");
        OQS_SIG_free(sig);
        return 1;
    }

    sig_len = fread(signature, 1, sizeof(signature), fs);
    fclose(fs);

    /* 4️⃣ Message to verify (same hash used during signing) */
    uint8_t message[64];  // e.g., SHA-512 digest
    for (int i = 0; i < 64; i++) message[i] = (uint8_t)i;

    /* 5️⃣ Verify */
    OQS_STATUS rc = OQS_SIG_verify(
        sig,
        message, sizeof(message),
        signature, sig_len,
        pk
    );

    if (rc == OQS_SUCCESS) {
        printf("Signature valid\n");
    } else {
        printf("Invalid signature\n");
    }

    OQS_SIG_free(sig);
    return 0;
}