#include <stdio.h>
#include <stdint.h>
#include <oqs/oqs.h>
#include <unistd.h>
#include <limits.h>

int main(void) {
    /* 1️⃣ Create Kyber KEM */
    OQS_KEM *kem = OQS_KEM_new("Kyber512");
    if (kem == NULL) {
        fprintf(stderr, "ERROR: Kyber512 not supported by liboqs\n");
        return 1;
    }
    char cwd[PATH_MAX];
    if (getcwd(cwd, sizeof(cwd)) != NULL) {
        printf("Current working directory: %s\n", cwd);
    } else {
        perror("getcwd() error");
    }
    /* 2️⃣ Load receiver public key */
    uint8_t pk[OQS_KEM_kyber_512_length_public_key];

    FILE *fpk = fopen("pqc_keys/receiver_kyber_pk.bin", "rb");
    
    if (!fpk) {
        fprintf(stderr, "ERROR: Could not open Kyber public key\n");
        OQS_KEM_free(kem);
        return 1;
    }

    fread(pk, 1, sizeof(pk), fpk);
    fclose(fpk);

    /* 3️⃣ Encapsulation */
    uint8_t ct[OQS_KEM_kyber_512_length_ciphertext];
    uint8_t ss[OQS_KEM_kyber_512_length_shared_secret];

    if (OQS_KEM_encaps(kem, ct, ss, pk) != OQS_SUCCESS) {
        fprintf(stderr, "ERROR: Kyber encapsulation failed\n");
        OQS_KEM_free(kem);
        return 1;
    }

    /* 4️⃣ Write ciphertext and shared secret */
    FILE *fct = fopen("pqc_keys/kyber_ct.bin", "wb");
    FILE *fss = fopen("pqc_keys/shared_secret_sender.bin", "wb");

    if (!fct || !fss) {
        fprintf(stderr, "ERROR: Could not write Kyber output files\n");
        OQS_KEM_free(kem);
        return 1;
    }

    fwrite(ct, 1, sizeof(ct), fct);
    fwrite(ss, 1, sizeof(ss), fss);

    fclose(fct);
    fclose(fss);

    OQS_KEM_free(kem);

    printf("Kyber encapsulation successful\n");
    return 0;
}