/*
 * Invoice Management System
 * -------------------------
 * A small menu program that keeps a list of invoices.
 * Each invoice has: an ID, a client name, a date, and a total amount.
 *
 * You can: add an invoice, show all invoices, find one by ID,
 * delete one, and see the grand total of all invoices.
 *
 * The list lives on the HEAP (malloc / realloc) so it can grow
 * as you add more invoices, and it is cleaned up with free() at the end.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* One invoice = one "record card" holding four pieces of information. */
typedef struct {
    int   id;            /* Invoice ID, e.g. 101            */
    char  client[50];    /* Client name, e.g. "Ali Traders" */
    char  date[11];      /* Date as text: "DD-MM-YYYY"      */
    float total;         /* Amount of money, e.g. 2500.50   */
} Invoice;

/* The "drawer" that holds all invoice cards. */
Invoice *invoices = NULL;  /* pointer to the list on the heap   */
int count    = 0;          /* how many invoices we have now     */
int capacity = 0;          /* how many fit before we must grow  */

/* Throw away leftover typing (e.g. letters typed where a number was expected). */
void clearInput(void) {
    int c;
    while ((c = getchar()) != '\n' && c != EOF);
}

/* Find the position of an invoice by its ID. Returns -1 if not found. */
int findInvoice(int id) {
    for (int i = 0; i < count; i++) {
        if (invoices[i].id == id) {
            return i;
        }
    }
    return -1;
}

/* Ask the user for invoice details and store them in the list. */
void addInvoice(void) {
    /* If the drawer is full, make it twice as big. */
    if (count == capacity) {
        int newCapacity = (capacity == 0) ? 2 : capacity * 2;
        Invoice *bigger = realloc(invoices, newCapacity * sizeof(Invoice));
        if (bigger == NULL) {
            printf("Out of memory! Could not add invoice.\n");
            return;
        }
        invoices = bigger;
        capacity = newCapacity;
    }

    Invoice inv;

    printf("Enter Invoice ID: ");
    if (scanf("%d", &inv.id) != 1) {
        printf("Invalid ID.\n");
        clearInput();
        return;
    }
    if (findInvoice(inv.id) != -1) {
        printf("An invoice with ID %d already exists.\n", inv.id);
        return;
    }

    printf("Enter Client Name: ");
    scanf(" %49[^\n]", inv.client);      /* reads a full name with spaces */

    printf("Enter Date (DD-MM-YYYY): ");
    scanf(" %10s", inv.date);

    printf("Enter Total Amount: ");
    if (scanf("%f", &inv.total) != 1 || inv.total < 0) {
        printf("Invalid amount.\n");
        clearInput();
        return;
    }

    invoices[count] = inv;   /* put the new card in the drawer */
    count++;
    printf("Invoice added successfully!\n");
}

/* Print every invoice as a neat table. */
void showAllInvoices(void) {
    if (count == 0) {
        printf("No invoices yet.\n");
        return;
    }
    printf("\n%-8s %-25s %-12s %12s\n", "ID", "Client", "Date", "Total");
    printf("---------------------------------------------------------------\n");
    for (int i = 0; i < count; i++) {
        printf("%-8d %-25s %-12s %12.2f\n",
               invoices[i].id, invoices[i].client,
               invoices[i].date, invoices[i].total);
    }
}

/* Look up one invoice by its ID and show it. */
void searchInvoice(void) {
    int id;
    printf("Enter Invoice ID to search: ");
    if (scanf("%d", &id) != 1) {
        printf("Invalid ID.\n");
        clearInput();
        return;
    }

    int pos = findInvoice(id);
    if (pos == -1) {
        printf("Invoice %d not found.\n", id);
        return;
    }
    printf("\nInvoice ID : %d\n",   invoices[pos].id);
    printf("Client     : %s\n",     invoices[pos].client);
    printf("Date       : %s\n",     invoices[pos].date);
    printf("Total      : %.2f\n",   invoices[pos].total);
}

/* Remove an invoice by its ID. */
void deleteInvoice(void) {
    int id;
    printf("Enter Invoice ID to delete: ");
    if (scanf("%d", &id) != 1) {
        printf("Invalid ID.\n");
        clearInput();
        return;
    }

    int pos = findInvoice(id);
    if (pos == -1) {
        printf("Invoice %d not found.\n", id);
        return;
    }

    /* Slide every invoice after it one step left to fill the gap. */
    for (int i = pos; i < count - 1; i++) {
        invoices[i] = invoices[i + 1];
    }
    count--;
    printf("Invoice %d deleted.\n", id);
}

/* Add up the totals of all invoices. */
void showGrandTotal(void) {
    float sum = 0;
    for (int i = 0; i < count; i++) {
        sum += invoices[i].total;
    }
    printf("Number of invoices: %d\n", count);
    printf("Grand total       : %.2f\n", sum);
}

int main(void) {
    int choice;

    do {
        printf("\n===== INVOICE MANAGEMENT SYSTEM =====\n");
        printf("1. Add Invoice\n");
        printf("2. Show All Invoices\n");
        printf("3. Search Invoice by ID\n");
        printf("4. Delete Invoice\n");
        printf("5. Show Grand Total\n");
        printf("0. Exit\n");
        printf("Enter your choice: ");

        int result = scanf("%d", &choice);
        if (result == EOF) {
            choice = 0;                  /* input ended: just exit */
        } else if (result != 1) {
            clearInput();                /* user typed letters, not a number */
            choice = -1;
        }

        switch (choice) {
            case 1: addInvoice();      break;
            case 2: showAllInvoices(); break;
            case 3: searchInvoice();   break;
            case 4: deleteInvoice();   break;
            case 5: showGrandTotal();  break;
            case 0: printf("Goodbye!\n"); break;
            default: printf("Invalid choice, try again.\n");
        }
    } while (choice != 0);

    free(invoices);   /* give the heap memory back before leaving */
    invoices = NULL;
    return 0;
}
