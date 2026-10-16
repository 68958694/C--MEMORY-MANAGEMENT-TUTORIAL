# Invoice Management System — Explained Simply

## What is it? (one line)
A small C program that **keeps a list of bills (invoices)** and lets you add, view, search, and delete them.

## What is an invoice?
A bill you give a customer. In this program, every invoice has 4 things:

| Field | Meaning | Example |
|---|---|---|
| Invoice ID | A unique number for the bill | `101` |
| Client name | Who the bill is for | `Ali Traders` |
| Date | When the bill was made | `12-10-2026` |
| Total | How much money | `2500.50` |

## Simple picture
- Think of each invoice as a **card**.
- All the cards go into a **drawer**.
- When the drawer is full, the program gets a **bigger drawer** automatically.
- When you exit, the program **empties the drawer** (gives memory back).

## The menu
```
1. Add Invoice          -> make a new card and put it in the drawer
2. Show All Invoices    -> print all cards as a table
3. Search Invoice by ID -> find one card by its number
4. Delete Invoice       -> take a card out
5. Show Grand Total     -> add up the money on all cards
0. Exit                 -> clean up and close
```

## Code parts in plain words
| Code | What it does |
|---|---|
| `struct Invoice` | The design of one card (ID, name, date, total). |
| `invoices`, `count`, `capacity` | The drawer, how many cards are in it, and how many it can hold. |
| `findInvoice()` | Looks at each card one by one until the ID matches. |
| `addInvoice()` | Asks you for the 4 details, checks the ID isn't used, saves the card. |
| `showAllInvoices()` | Prints every card in a neat table. |
| `searchInvoice()` | Finds and prints one card. |
| `deleteInvoice()` | Removes a card and slides the rest up to close the gap. |
| `showGrandTotal()` | Adds all totals together. |
| `clearInput()` | Throws away wrong typing (e.g. letters instead of a number). |
| `main()` | Shows the menu again and again until you choose 0. |

## Link to memory management (this repo's topic)
- `realloc()` asks the **heap** for more space when the list gets full.
- `free()` gives that space back at the end, so there is **no memory leak**.

## How to run
```bash
gcc invoice.c -o invoice
./invoice
```

## Say it in 2 sentences
"This program is a digital notebook for bills. It stores each bill's ID, client name, date, and amount, and lets you add, list, search, delete, and total them."
