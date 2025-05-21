import os
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import message_dialog, button_dialog, input_dialog
import sys
import toml
import types
import typing as t


config = types.SimpleNamespace(**toml.load("settings.toml"))


def round_down(number: float, decimal_places: t.Optional[int]=2) -> float:
    """
    Round down according to the library's rules. Prices are
    rounded down to the nearest nickel.

    Args:
        number: The number to round down.
        decimal_places: The number of decimal places to round to.
    
    Returns:
        The rounded down float.
    """
    number = round(number, decimal_places)
    
    if len(str(number).split(".")[-1]) == 1:
        return float(number)
    
    if str(number).endswith("0") or str(number).endswith("5"):
        return number
    
    if str(number)[-1] in ["1", "2", "3", "4"]:
        if len(str(number).split(".")[-1]) > 1:
            return float(f"{str(number)[0:-1]}0")
        else:
            return float(f"{str(number)}0")
    else:
        return float(f"{str(number)[0:-1]}5")


def format_currency(number) -> str:
    """
    Format a number as a string for currency representation.

    Args:
        number: The number format for currency.
    
    Returns:
        A string containing the formatted number.
    """
    if len(str(number).split(".")[-1]) == 1:
        return f"{number}0"
    else:
        return str(number)


def resource_path(relative_path: str) -> str:
    """
    Obtain a resource path from a relative path. This is used
    to access resources when the program is compiled to a binary
    for production use.

    Args:
        relative_path: A string containing the relative path.
    
    Returns:
        A string containing the resource path.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Before importing the printer connection library, we have to
# set the resource path for the printer's capabilities.
os.environ['ESCPOS_CAPABILITIES_FILE'] = resource_path("assets/capabilities.json")
from escpos.printer import Serial


class MakeItReceiptPrinter:
    """
    Class abstracts a receipt printer.

    Attributes:
        self._printer: The serial connection to the actual receipt printer.
    """
    def __init__(self):
        self._printer = Serial(devfile=config.SERIAL_PORT)
        self._printer.close()
    
    def _print_header(self) -> None:
        """Print the header of the receipt."""
        self._printer.set(align='center', normal_textsize=True)
        self._printer.image(resource_path("assets/makeit.png"))
        self._printer.text("Northville District Library\n")
    
    def _print_footer(self) -> None:
        """Print the footer of the receipt."""
        self._printer.text("\n\n")

    def print_sublimation(self, pages: int, cups: t.Optional[int]=0) -> None:
        """
        Print a receipt for sublimation.

        During sublimation printing, we charge a fixed rate for each
        sheet of transfer paper consumed in the printing process. We
        also optionally have mugs available for sale to use as blanks.

        Args:
            pages: The number of pages printed.
            cups: The number of cups used.

        Returns:
            None
        """
        self._printer.open()
        self._print_header()

        self._printer.set(align='center')
        self._printer.text("Sublimation\n\n")

        self._printer.set(align='left')
        self._printer.set(double_height=True, double_width=True)

        self._printer.text(f"Pages:  {pages}\n")
        self._printer.text(f"Rate:   ${format_currency(config.SUBLIMATION_RATE)}/page\n")
        
        # Omit printing of the cup portion if no cups are used.
        if cups != 0:
            self._printer.text(f"Mugs:   {cups}\n")
            self._printer.text(f"Rate:   ${format_currency(config.MUG_RATE)}/mug\n\n")

        cost = (pages * config.SUBLIMATION_RATE) + (cups * config.MUG_RATE)
        self._printer.text(f"Cost:   ${format_currency(cost)}\n\n")
        self._print_footer()
        self._printer.cut()
        self._printer.close()


    def print_3dp(self, name: str, weight: float) -> None:
        """
        Print a receipt for 3D printing.

        We charge a fixed rate by weight for 3D printing.

        Args:
            name: The name of the patron who requested the job.
            weight: The final weight of all parts in grams.

        Returns:
            None
        """
        self._printer.open()
        
        self._print_header()

        cost = weight * config.FILAMENT_RATE

        self._printer.set(align='center')
        self._printer.text("3D Print Job\n\n")

        self._printer.set(align='left')
        self._printer.set(double_height=True, double_width=True)
        self._printer.text(f"{name}\n\n")

        self._printer.text(f"Weight: {weight}g\n")
        self._printer.text(f"Rate:   ${config.FILAMENT_RATE}/g\n\n")
        self._printer.text(f"Cost:   ${format_currency(round_down(cost))}\n\n")
        self._print_footer()
        self._printer.cut()
        self._printer.close()



class ReceiptOMatic:
    """
    Class abstracts the program itself.

    Attributes:
        self.printer: A MakeItReceiptPrinter which allows us to print.
    """
    def __init__(self):
        self.printer = MakeItReceiptPrinter()

    def main(self) -> None:
        """Main function which starts the program."""
        result = button_dialog(
            title="Receipt-O-Matic",
            text="Select an option...",
            buttons=[
                ('3D Printing', "prompt_3dp"),
                ('Sublimation', "prompt_sub"),
                ('Quit', "quit")
            ]
        ).run()

        getattr(self, result)()
    
    def prompt_type(self, type_caster: t.Callable, title: str, text: str) -> float:
        """
        Prompts the user for a particular type of information.

        The prompt toolkit obtains information in the form of a string. However,
        sometimes we specifically want a number, and would want to repeatedly ask for
        a number in the event that a user enters something invalid.

        Args:
            type_caster: The casting function for the type requested. (Ex. int(), float(), etc...)
            title: A string containing the title of the TUI window.
            text: The text to be displayed during the prompt.
        
        Returns:
            A float containing the number entered during the prompt.
        """
        try:
            number = input_dialog(
                title=title,
                text=text
            ).run()
            number = type_caster(number)
        except ValueError:
            message_dialog(
                title=title,
                text=f"Invalid entry '{number}'"
            )
            return self.prompt_type(type_caster, title, text)
        return number
    
    def prompt_3dp(self) -> None:
        """
        Prompts the user for the information of a 3D print job,
        then prints the receipt for said job.
        
        Returns:
            None
        """
        name = input_dialog(
            title="3D Print Job",
            text="Enter Patron's Name:"
        ).run()

        weight = self.prompt_type(
            float,
            "3D Print Job",
            "Enter the weight in grams:"
        )
        self.printer.print_3dp(name, weight)
        self.main()
    
    def prompt_sub(self) -> None:
        """
        Prompts the user for the information of a sublimation job,
        then prints the receipt for said job.
        
        Returns:
            None
        """
        pages = self.prompt_type(
            int,
            "Sublimation",
            "Enter the number of pages printed:"
        )

        mugs = self.prompt_type(
            int,
            "Sublimation",
            "Enter the number of mugs purchased:"
        )
        self.printer.print_sublimation(pages, cups=mugs)
        self.main()
    
    def quit(self) -> None:
        """Exits the program."""
        sys.exit(0)


if __name__ == "__main__":
    ReceiptOMatic().main()

