from aiogram.fsm.state import State,StatesGroup
class InputFlow(StatesGroup): search=State(); jump_result=State(); jump_image=State()
